"""
Spam detection module for ComparIA.

This module provides simple regex-based spam detection using patterns
defined in spam_patterns.json. Patterns can be updated without code changes.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from fastapi import Request

logger = logging.getLogger("languia")

# Cache compiled patterns to avoid recompiling on each request
_compiled_patterns: Optional[list[tuple[str, re.Pattern, str]]] = None
_patterns_file_mtime: Optional[float] = None


def _get_patterns_file_path() -> Path:
    """Get the path to spam_patterns.json."""
    return Path(__file__).parent / "spam_patterns.json"


def _parse_regex_flags(flags_str: str) -> int:
    """
    Parse regex flags from string to re module flags.

    Args:
        flags_str: Pipe-separated flags like "IGNORECASE|DOTALL"

    Returns:
        Combined re flags
    """
    flag_map = {
        "IGNORECASE": re.IGNORECASE,
        "MULTILINE": re.MULTILINE,
        "DOTALL": re.DOTALL,
        "ASCII": re.ASCII,
        "VERBOSE": re.VERBOSE,
    }

    flags = 0
    for flag_name in flags_str.split("|"):
        flag_name = flag_name.strip()
        if flag_name in flag_map:
            flags |= flag_map[flag_name]

    return flags


def _load_spam_patterns() -> list[tuple[str, re.Pattern, str]]:
    """
    Load spam patterns from JSON file and compile them.

    Returns:
        List of (name, compiled_pattern, description) tuples
    """
    patterns_file = _get_patterns_file_path()

    if not patterns_file.exists():
        logger.warning(f"Spam patterns file not found: {patterns_file}")
        return []

    try:
        with open(patterns_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        compiled = []
        for pattern_def in data.get("patterns", []):
            if not pattern_def.get("enabled", True):
                continue

            name = pattern_def["name"]
            regex = pattern_def["regex"]
            flags = _parse_regex_flags(pattern_def.get("flags", ""))
            description = pattern_def.get("description", "")

            try:
                compiled_pattern = re.compile(regex, flags)
                compiled.append((name, compiled_pattern, description))
                logger.debug(f"Loaded spam pattern: {name}")
            except re.error as e:
                logger.error(f"Invalid regex in pattern '{name}': {e}")

        logger.info(f"Loaded {len(compiled)} spam detection patterns")
        return compiled

    except Exception as e:
        logger.error(f"Failed to load spam patterns: {e}", exc_info=True)
        return []


def _get_compiled_patterns() -> list[tuple[str, re.Pattern, str]]:
    """
    Get compiled patterns, reloading if file has changed.

    This allows hot-reloading of patterns without restarting the server.
    """
    global _compiled_patterns, _patterns_file_mtime

    patterns_file = _get_patterns_file_path()

    if not patterns_file.exists():
        return []

    current_mtime = patterns_file.stat().st_mtime

    # Reload if file changed or patterns not loaded yet
    if _compiled_patterns is None or _patterns_file_mtime != current_mtime:
        _compiled_patterns = _load_spam_patterns()
        _patterns_file_mtime = current_mtime

    return _compiled_patterns


def is_spam(prompt: str) -> bool:
    """
    Check if a prompt matches known spam patterns.

    Args:
        prompt: User prompt to check

    Returns:
        True if prompt is spam, False otherwise
    """
    patterns = _get_compiled_patterns()

    if not patterns:
        # No patterns loaded, consider as not spam
        return False

    for name, pattern, description in patterns:
        if pattern.search(prompt):
            return True

    return False


def validate_prompt_not_spam(prompt: str, request: Request) -> None:
    """
    Validate that a prompt doesn't match known spam patterns.

    Args:
        prompt: User prompt to validate
        request: FastAPI request for logging

    Raises:
        ValueError: If prompt matches a spam pattern
    """
    patterns = _get_compiled_patterns()

    if not patterns:
        # No patterns loaded, allow prompt
        return

    for name, pattern, description in patterns:
        if pattern.search(prompt):
            logger.warning(
                f"Spam detected - pattern '{name}' matched: {description}",
                extra={
                    "request": request,
                    "pattern": name,
                    "prompt_preview": prompt[:100],
                },
            )
            raise ValueError(
                f"This prompt format is not allowed. Please use natural language."
            )

    logger.debug(f"Prompt passed spam validation ({len(patterns)} patterns checked)")
