"""Report display units for the selected electrical nodes."""

from collections.abc import Iterable


def report_cost_unit(node_names: Iterable[str]) -> str:
    """Show pesos only when Chaca 110 is the sole selected series."""
    return "CLP/kWh" if set(node_names) == {"Chaca 110"} else "USD/MWh"
