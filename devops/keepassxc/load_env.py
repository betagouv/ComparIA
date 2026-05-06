"""
Load KeePass entries from a group as environment variables.

Entry username = variable name, entry password = variable value.
Outputs shell export statements to stdout — designed to be eval'd.

The master password is cached in the OS keychain (via keyring) for --timeout
seconds (default 28800 = 8h). Set --timeout 0 to disable caching.

Usage:
    eval $(uv run --group devops python devops/keepassxc/load_env.py \
        --db ~/secrets.kdbx \
        --group "comparia/instances/fr")

In .envrc (direnv):
    eval $(uv run --group devops python $PWD/devops/keepassxc/load_env.py \
        --db ~/secrets.kdbx \
        --group "comparia/instances/fr")
"""

import getpass
import json
import os
import sys
import time
from pathlib import Path

import cyclopts
import keyring
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

app = cyclopts.App()

_KEYRING_SERVICE = "load_env_keepass"


def _cached_password(db: Path, timeout: int) -> str | None:
    if timeout <= 0:
        return None
    raw = keyring.get_password(_KEYRING_SERVICE, str(db.resolve()))
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        if time.time() - data["ts"] < timeout:
            return data["pw"]
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _store_password(db: Path, password: str) -> None:
    keyring.set_password(
        _KEYRING_SERVICE,
        str(db.resolve()),
        json.dumps({"pw": password, "ts": time.time()}),
    )


def find_group(kp: PyKeePass, path: str):
    parts = [p for p in path.split("/") if p]
    current = kp.root_group
    for part in parts:
        found = kp.find_groups(name=part, group=current, first=True)
        if found is None:
            print(f"# error: group '{part}' not found in '{path}'", file=sys.stderr)
            sys.exit(1)
        current = found
    return current


@app.default
def main(
    db: Path,
    group: str,
    timeout: int = 28800,
    mask: bool = False,
):
    """
    --timeout: password cache duration in seconds (default 28800 = 8h, 0 = disabled)
    --mask: print VAR=*** instead of the actual values
    """
    password = (
        os.environ.get("KEEPASS_PASSWORD")
        or _cached_password(db, timeout)
        or getpass.getpass(f"KeePass password [{db.name}]: ", stream=sys.stderr)
    )

    try:
        kp = PyKeePass(str(db), password=password)
    except CredentialsError:
        print("# error: wrong password", file=sys.stderr)
        sys.exit(1)

    if timeout > 0 and not os.environ.get("KEEPASS_PASSWORD"):
        _store_password(db, password)

    target = find_group(kp, group)
    entries = kp.find_entries(group=target, recursive=False)

    if not entries:
        print(f"# warning: no entries found in '{group}'", file=sys.stderr)
        return

    for entry in entries:
        name = entry.username
        value = entry.password or ""
        if not name:
            continue
        if mask:
            print(f"export {name}='***'")
        else:
            safe_value = value.replace("'", "'\\''")
            print(f"export {name}='{safe_value}'")


if __name__ == "__main__":
    app()
