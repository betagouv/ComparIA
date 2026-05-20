"""
Spam detection module for ComparIA.

Loads spam patterns from spam_patterns.json and provides is_spam() function
for use in dataset export filtering.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("languia")

_compiled_patterns: Optional[list[re.Pattern]] = None

# Zero-width and invisible characters used by bots to evade regex matching
# (e.g. inserting U+200D between letters of 'say' so 'say ok' patterns miss).
_INVISIBLE_CHARS = re.compile("[​-‏‪-‮⁠-⁯﻿]")


def _load_spam_patterns() -> list[re.Pattern]:
    """Load and compile spam patterns from JSON file."""
    patterns_file = Path(__file__).parent / "spam_patterns.json"

    if not patterns_file.exists():
        logger.warning(f"Spam patterns file not found: {patterns_file}")
        return []

    flag_map = {
        "IGNORECASE": re.IGNORECASE,
        "MULTILINE": re.MULTILINE,
        "DOTALL": re.DOTALL,
        "ASCII": re.ASCII,
        "VERBOSE": re.VERBOSE,
    }

    try:
        with open(patterns_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        compiled = []
        for pattern_def in data.get("patterns", []):
            if not pattern_def.get("enabled", True):
                continue

            name = pattern_def["name"]
            regex = pattern_def["regex"]
            flags = sum(
                flag_map.get(f.strip(), 0)
                for f in pattern_def.get("flags", "").split("|")
            )

            try:
                compiled_pattern = re.compile(regex, flags)
                compiled.append(compiled_pattern)
                logger.debug(f"Loaded spam pattern: {name}")
            except re.error as e:
                logger.error(f"Invalid regex in pattern '{name}': {e}")

        logger.info(f"Loaded {len(compiled)} spam detection patterns")
        return compiled

    except Exception as e:
        logger.error(f"Failed to load spam patterns: {e}", exc_info=True)
        return []


def is_spam(prompt: str) -> bool:
    """
    Check if a prompt matches spam patterns.

    Args:
        prompt: User prompt to check

    Returns:
        True if prompt is spam, False otherwise
    """
    global _compiled_patterns
    if _compiled_patterns is None:
        _compiled_patterns = _load_spam_patterns()

    normalized = _INVISIBLE_CHARS.sub("", prompt)
    return any(pattern.search(normalized) for pattern in _compiled_patterns)
