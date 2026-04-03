"""
Load KeePass entries from a group as environment variables.

Entry username = variable name, entry password = variable value.
Outputs shell export statements to stdout — designed to be eval'd.

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
import os
import sys
from pathlib import Path

import cyclopts
from pykeepass import PyKeePass
from pykeepass.exceptions import CredentialsError

app = cyclopts.App()


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
):
    password = os.environ.get("KEEPASS_PASSWORD") or getpass.getpass(
        f"KeePass password [{db.name}]: ", stream=sys.stderr
    )

    try:
        kp = PyKeePass(str(db), password=password)
    except CredentialsError:
        print("# error: wrong password", file=sys.stderr)
        sys.exit(1)

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
        # escape single quotes in value
        safe_value = value.replace("'", "'\\''")
        print(f"export {name}='{safe_value}'")


if __name__ == "__main__":
    app()
