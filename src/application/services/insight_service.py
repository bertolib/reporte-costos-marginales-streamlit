"""Rule-based insight generation for the first platform iteration."""

import pandas as pd


class InsightService:
    """Generate transparent, data-backed executive observations."""

    def build_initial_insights(self, observations: pd.DataFrame) -> list[str]:
        """Return concise observations without inventing external causes."""
        if observations.empty:
            return ["No hay datos disponibles para el periodo seleccionado."]

        insights: list[str] = []
        latest = observations["timestamp"].max()
        last_7 = observations[observations["timestamp"] > latest - pd.Timedelta(days=7)]
        previous_7 = observations[
            (observations["timestamp"] <= latest - pd.Timedelta(days=7))
            & (observations["timestamp"] > latest - pd.Timedelta(days=14))
        ]

        if not last_7.empty and not previous_7.empty:
            by_node_current = last_7.groupby("node_name")["value"].mean()
            by_node_previous = previous_7.groupby("node_name")["value"].mean()
            variation = ((by_node_current / by_node_previous) - 1).dropna().sort_values(ascending=False)
            if not variation.empty:
                top_node = variation.index[0]
                insights.append(
                    f"La mayor variación semanal promedio se observa en {top_node}: "
                    f"{variation.iloc[0] * 100:.1f}% frente a los 7 días previos."
                )

        peak = observations.loc[observations["value"].idxmax()]
        insights.append(
            f"El máximo del periodo fue {peak['value']:.2f} USD/MWh en "
            f"{peak['node_name']} el {peak['timestamp']:%d-%m-%Y %H:%M}."
        )

        spread = observations.groupby("node_name")["value"].mean().sort_values(ascending=False)
        if spread.shape[0] >= 2:
            insights.append(
                f"La barra con mayor promedio fue {spread.index[0]} y la menor fue "
                f"{spread.index[-1]}, con una brecha promedio de {spread.iloc[0] - spread.iloc[-1]:.2f} USD/MWh."
            )

        return insights
