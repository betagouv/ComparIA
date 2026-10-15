"""
US dollars as the limits count them. The expensive allowances and each
model's day are Redis counters in millionths of a dollar, so they stay whole
numbers; the admin sets and reads dollars, to the cent.
"""

MICRO_USD = 1_000_000
# Cents in a dollar, the smallest step the admin edits dollars in.
CENTS = 100


def to_micro_usd(usd: float) -> int:
    return round(usd * MICRO_USD)


def to_usd(micro_usd: float) -> float:
    return micro_usd / MICRO_USD


def shown_usd(usd: float, places: int = 2) -> str:
    """Dollars as the logs and the CLI print them: "$1,234.50"."""
    return f"${usd:,.{places}f}"
