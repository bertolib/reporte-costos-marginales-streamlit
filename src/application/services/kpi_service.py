"""Executive KPI calculations."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ExecutiveKpis:
    """Main executive KPI payload."""

    average_cost: float
    max_cost: float
    min_cost: float
    weekly_variation_pct: float | None
    monthly_variation_pct: float | None
    annual_variation_pct: float | None
    observations: int
    last_timestamp: pd.Timestamp | None


class KpiService:
    """Compute executive market indicators."""

    def build_executive_kpis(self, observations: pd.DataFrame) -> ExecutiveKpis:
        """Compute KPIs for the provided observation set."""
        if observations.empty:
            return ExecutiveKpis(0, 0, 0, None, None, None, 0, None)

        latest = observations["timestamp"].max()
        current_window_start = latest - pd.Timedelta(days=7)
        previous_window_start = latest - pd.Timedelta(days=14)

        current_week = observations[observations["timestamp"] > current_window_start]
        previous_week = observations[
            (observations["timestamp"] <= current_window_start)
            & (observations["timestamp"] > previous_window_start)
        ]

        current_month = observations[
            (observations["timestamp"].dt.year == latest.year)
            & (observations["timestamp"].dt.month == latest.month)
        ]
        previous_month_date = latest - pd.DateOffset(months=1)
        previous_month = observations[
            (observations["timestamp"].dt.year == previous_month_date.year)
            & (observations["timestamp"].dt.month == previous_month_date.month)
        ]

        previous_year = observations[
            (observations["timestamp"].dt.year == latest.year - 1)
            & (observations["timestamp"].dt.month == latest.month)
        ]

        return ExecutiveKpis(
            average_cost=round(float(observations["value"].mean()), 2),
            max_cost=round(float(observations["value"].max()), 2),
            min_cost=round(float(observations["value"].min()), 2),
            weekly_variation_pct=self._variation(current_week["value"].mean(), previous_week["value"].mean()),
            monthly_variation_pct=self._variation(current_month["value"].mean(), previous_month["value"].mean()),
            annual_variation_pct=self._variation(current_month["value"].mean(), previous_year["value"].mean()),
            observations=int(observations.shape[0]),
            last_timestamp=latest,
        )

    @staticmethod
    def _variation(current: float, previous: float) -> float | None:
        if pd.isna(current) or pd.isna(previous) or previous == 0:
            return None
        return round(float((current / previous - 1) * 100), 1)
