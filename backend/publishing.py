"""
Fire the publish run on a schedule, from inside the backend.

Not a service of its own: several instances run as a single container next to
their own Postgres, and anything asking an operator to add a service to their
compose file does not get deployed. The export itself still runs as a child
process, so a multi-gigabyte parquet build cannot take the memory the arena is
serving from.

Replicas elect one scheduler between them with a Postgres advisory lock. The
rest wait for it, so losing the replica that holds it hands the schedule to a
neighbour rather than stopping it. DATASET_SCHEDULER_ENABLED=false turns it
off, which lets a larger deployment run this same image as a dedicated
scheduler replica.
"""

import asyncio
import logging
import os
import resource
import sys
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from backend.config import settings
from utils.database.models.app_settings import AppSettings
from utils.database.session import get_engine
from utils.database.settings import get_app_settings
from utils.dataset.runs import close_unfinished_run, last_run

logger = logging.getLogger("comparia.publishing")

# Any constant will do, as long as every replica picks the same one.
ADVISORY_LOCK_KEY = 8_147_231

# How often the loop looks at the schedule. Small enough that an hour changed
# in the panel takes effect the same day, large enough to be free.
TICK_SECONDS = 60


def _at_hour(local: datetime, hour: int) -> datetime:
    """
    That day at that hour, in the same zone.

    On the day the clocks go forward the hour may not exist, and asking for it
    gives a moment that is really the hour before or after. The run then fires
    at the wrong time once a year, or twice on the day they go back. Where the
    hour is missing we take the next one that exists; where it happens twice we
    take the first, which 'fold=0' already does.
    """
    zone = local.tzinfo
    for offset in range(3):
        due = local.replace(
            hour=(hour + offset) % 24, minute=0, second=0, microsecond=0, fold=0
        )
        # An hour the clocks skipped comes back as a different one.
        if due.astimezone(UTC).astimezone(zone).hour == due.hour:
            return due
    return local.replace(hour=hour, minute=0, second=0, microsecond=0, fold=0)


def next_run_at(app_settings: AppSettings, after: datetime) -> datetime | None:
    """
    The next moment the run is due, in UTC. Weekly means Monday, monthly means
    the first of the month, both at the configured hour. A frequency, an hour
    and a time zone rather than a cron expression: a mistyped cron expression
    is an export every minute.

    Nothing catches up. A run missed because the process was down waits for
    the next occurrence rather than firing at boot, when an operator is
    already busy with whatever brought the process down.
    """
    frequency = app_settings.publish_frequency
    if frequency == "off":
        return None

    zone = ZoneInfo(app_settings.publish_timezone)
    local = after.astimezone(zone)

    def due_on(day: date) -> datetime:
        # The hour is worked out per day, because whether it exists depends on
        # the day: 02:00 is missing on the morning the clocks go forward and
        # back the morning after.
        return _at_hour(datetime.combine(day, time(), tzinfo=zone), hour)

    hour = app_settings.publish_hour
    day = local.date()

    if frequency == "daily":
        if due_on(day) <= local:
            day += timedelta(days=1)
    elif frequency == "weekly":
        day += timedelta(days=(7 - day.weekday()) % 7)
        if due_on(day) <= local:
            day += timedelta(days=7)
    elif frequency == "monthly":
        day = day.replace(day=1)
        if due_on(day) <= local:
            # The 28th of any month plus four days is always the next month.
            day = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    else:
        return None

    return due_on(day).astimezone(UTC)


def _child_limits() -> None:
    """
    Runs in the child, between fork and exec. It gives way to the arena rather
    than competing with it, and it cannot grow past its share of the machine.
    """
    os.nice(10)
    limit = settings.DATASET_MEMORY_LIMIT_GB * 1024**3
    try:
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    except (ValueError, OSError):
        # Some platforms refuse an address space limit. The watchdog and the
        # disk check still apply.
        pass


async def run_export() -> None:
    """
    Start the export as a child process and watch it. It gets a wall clock
    watchdog: a run that hangs on a destination that never answers must not
    hold the schedule for ever.
    """
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "utils.dataset.run",
        "--record",
        preexec_fn=_child_limits,
    )
    logger.info(f"Publish run started, pid {process.pid}")

    try:
        code = await asyncio.wait_for(
            process.wait(), timeout=settings.DATASET_RUN_TIMEOUT
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        logger.error(f"Publish run killed after {settings.DATASET_RUN_TIMEOUT} seconds")
        await close_unfinished_run(
            f"Killed after {settings.DATASET_RUN_TIMEOUT} seconds"
        )
        return

    if code == 0:
        logger.info("Publish run finished")
    else:
        logger.error(f"Publish run exited with code {code}")
        # A child killed by the kernel, or one that died before it could write
        # its own failure, leaves the row open behind it.
        await close_unfinished_run(f"The export exited with code {code}")


async def _hold_lock(connection) -> bool:
    result = await connection.exec_driver_sql(
        f"SELECT pg_try_advisory_lock({ADVISORY_LOCK_KEY})"
    )
    taken = bool(result.scalar())
    # The lock belongs to the session, not the transaction, so it survives this
    # commit. Without it the connection would sit idle in a transaction for as
    # long as the process lives, and a transaction that old holds vacuum back
    # across the whole database.
    await connection.commit()
    return taken


async def _release_lock(connection) -> None:
    """
    A dying process releases the lock by closing its connection. A dying task
    does not: its connection goes back to the pool still holding it, and no
    other replica could ever take the schedule over.
    """
    await connection.exec_driver_sql(f"SELECT pg_advisory_unlock({ADVISORY_LOCK_KEY})")
    await connection.commit()


async def scheduler() -> None:
    engine = get_engine()
    if engine is None:
        return

    async with engine.connect() as connection:
        # Whoever holds the lock is the scheduler. The others keep asking, so
        # that a replica going down hands the schedule to one of its
        # neighbours within the minute rather than stopping it until someone
        # notices and restarts something.
        while not await _hold_lock(connection):
            await asyncio.sleep(TICK_SECONDS)
        logger.info("Holding the publish scheduler")

        try:
            # A run interrupted by a restart left its row open; nothing else
            # will ever close it.
            await close_unfinished_run("The process stopped while the run was going")

            # The due time is worked out once per schedule, not once per tick:
            # next_run_at always answers with a future moment, so recomputing
            # it every minute would push the run away for ever.
            schedule: tuple | None = None
            due: datetime | None = None

            while True:
                await asyncio.sleep(TICK_SECONDS)
                now = datetime.now(UTC)
                app_settings = await get_app_settings()

                current = (
                    app_settings.publish_frequency,
                    app_settings.publish_hour,
                    app_settings.publish_timezone,
                )
                if current != schedule:
                    schedule = current
                    due = next_run_at(app_settings, now)
                    logger.info(
                        f"Next publish run: {due or 'never, the schedule is off'}"
                    )

                if due is None or now < due:
                    continue

                run = await last_run()
                if run is not None and run.finished_at is None:
                    logger.warning("A publish run is already going, skipping this one")
                else:
                    await run_export()
                due = next_run_at(app_settings, datetime.now(UTC))
        finally:
            await _release_lock(connection)


def start(app) -> None:
    """Called from the lifespan. Keeps a reference so the task is not collected."""
    if not settings.DATASET_SCHEDULER_ENABLED or get_engine() is None:
        return
    app.state.publish_scheduler = asyncio.create_task(scheduler())


async def stop(app) -> None:
    """
    Stop the loop, and wait for it: cancelling without waiting leaves the
    lock's connection to the garbage collector, which cannot close it cleanly.
    """
    task = getattr(app.state, "publish_scheduler", None)
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
