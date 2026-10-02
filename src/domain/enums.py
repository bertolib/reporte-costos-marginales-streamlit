"""Domain enumerations."""

from enum import StrEnum


class Granularity(StrEnum):
    """Supported market data granularities."""

    DAILY = "daily"
    HOURLY = "hourly"
    FIFTEEN_MINUTES = "15min"


class Scenario(StrEnum):
    """Observed or projected data state."""

    ACTUAL = "actual"
    PROJECTED = "projected"
