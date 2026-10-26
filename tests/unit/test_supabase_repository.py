from types import SimpleNamespace

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.domain.enums import Granularity
from src.infrastructure.repositories.supabase_market_repository import SupabaseMarketRepository


def test_hourly_aggregation_preserves_missing_values_and_source_groups():
    repository = object.__new__(SupabaseMarketRepository)
    records = [
        {"timestamp": "2026-10-18 00:00:00", "source_file": "a.tsv",
         "cmg_mej_110_usd_mwh": "10", "cmg_chacaya_110_usd_mwh": None},
        {"timestamp": "2026-10-18 00:15:00", "source_file": "a.tsv",
         "cmg_mej_110_usd_mwh": None, "cmg_chacaya_110_usd_mwh": "30"},
        {"timestamp": "2026-10-18 00:30:00", "source_file": "b.tsv",
         "cmg_mej_110_usd_mwh": "20", "cmg_chacaya_110_usd_mwh": "50"},
    ]
    repository._fetch_all_records = lambda: records
    expected = repository._to_hourly(repository.load_observations(Granularity.FIFTEEN_MINUTES))
    actual = repository.load_observations(Granularity.HOURLY)
    keys = ["timestamp", "node_id", "source"]
    assert_frame_equal(actual.sort_values(keys).reset_index(drop=True),
                       expected.sort_values(keys).reset_index(drop=True), check_like=True)


@pytest.mark.parametrize("truncate", [False, True])
def test_parallel_download_preserves_page_order_and_rejects_missing_rows(truncate):
    rows = [{"timestamp": str(index)} for index in range(7)]

    class Query:
        def select(self, *args, **kwargs):
            return self

        def order(self, *args):
            return self

        def range(self, start, end):
            self.start, self.end = start, end
            return self

        def execute(self):
            batch = rows[self.start:self.end + 1]
            if truncate and self.start == 3:
                batch = batch[:-1]
            return SimpleNamespace(data=batch, count=len(rows))

    repository = object.__new__(SupabaseMarketRepository)
    repository.client = SimpleNamespace(table=lambda _: Query())
    repository.table_name = "test"
    repository.page_size = 3
    if truncate:
        with pytest.raises(RuntimeError, match="incomplete"):
            repository._fetch_all_records()
    else:
        assert repository._fetch_all_records() == rows
