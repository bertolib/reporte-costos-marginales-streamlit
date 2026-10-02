"""Canonical domain entities."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.enums import Granularity, Scenario


@dataclass(frozen=True)
class ElectricalNode:
    """Electrical node used to organize marginal cost observations."""

    node_id: str
    name: str
    zone: str
    voltage_kv: int | None


@dataclass(frozen=True)
class MarketObservation:
    """Canonical representation of a marginal cost observation."""

    timestamp: datetime
    node_id: str
    node_name: str
    zone: str
    value: float
    unit: str
    granularity: Granularity
    scenario: Scenario
    source: str
