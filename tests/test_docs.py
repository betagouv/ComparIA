"""
Keeps the docs from lying.

Two checks, both cheap:
  - every `make ...` a doc tells you to run is a real Makefile target
  - every setting in backend/config.py is mentioned in .env.example

Both caught real rot: `make models-build` survived in two guides for months
after the target was deleted, and .env.example was missing ALTCHA_HMAC_KEY,
which the self-hosting guide lists as required.

Run with pytest, or directly:
    uv run python tests/test_docs.py
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Set from the environment or by the deploy, never by a human editing .env.
NOT_IN_ENV_EXAMPLE = {
    "GIT_COMMIT",  # injected at build time
    "LOGDIR",  # derived from the repo root
    "LANGUIA_CONTROLLER_URL",  # legacy, only read on an error path
}


def tracked_markdown() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [ROOT / line for line in out.splitlines() if line]


def code_blocks(text: str) -> str:
    """Just the fenced blocks, so prose like "make participation" is ignored."""
    return "\n".join(re.findall(r"^```[^\n]*\n(.*?)^```", text, re.S | re.M))


def makefile_targets() -> set[str]:
    makefile = (ROOT / "Makefile").read_text()
    return set(re.findall(r"^([a-zA-Z0-9_-]+):", makefile, re.M))


def settings_fields() -> set[str]:
    config = (ROOT / "backend" / "config.py").read_text()
    return set(re.findall(r"^    ([A-Z][A-Z0-9_]*)\s*:", config, re.M))


def test_docs_only_reference_real_make_targets():
    targets = makefile_targets()
    broken = []

    for path in tracked_markdown():
        for command in re.findall(r"\bmake ([a-z0-9-]+)", code_blocks(path.read_text())):
            if command not in targets:
                broken.append(f"{path.relative_to(ROOT)} says `make {command}`")

    assert not broken, "docs reference make targets that do not exist:\n" + "\n".join(
        sorted(set(broken))
    )


def test_env_example_covers_every_setting():
    example = (ROOT / ".env.example").read_text()
    missing = sorted(
        field
        for field in settings_fields() - NOT_IN_ENV_EXAMPLE
        if not re.search(rf"^#?\s*(export )?{field}=", example, re.M)
    )

    assert not missing, (
        ".env.example is the config reference, so every setting belongs in it "
        "(commented out is fine). Missing:\n" + "\n".join(missing)
    )


if __name__ == "__main__":
    test_docs_only_reference_real_make_targets()
    test_env_example_covers_every_setting()
    print("docs ok")
