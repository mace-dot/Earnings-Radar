from engine.run import universe


def test_directory_refresh_batches_uniform_keys_without_erasing_enrichment(monkeypatch):
    monkeypatch.setattr(
        "engine.run.SEC.securities",
        lambda _: [
            {"symbol": "KNOWN", "asset_type": "unverified", "sector": "Unclassified"},
            {"symbol": "NEW", "asset_type": "unverified", "sector": "Unclassified"},
        ],
    )

    class Database:
        written = []

        def pages(self, table, params):
            return [
                {
                    "symbol": "KNOWN",
                    "asset_type": "common_stock",
                    "listing_metadata": {"source": "fixture exchange"},
                    "sector": "Technology",
                    "industry": "Semiconductors",
                }
            ]

        def write(self, table, rows, conflict):
            assert table == "securities" and conflict == "symbol"
            assert len({tuple(sorted(row)) for row in rows}) == 1
            self.written.extend(rows)

    database = Database()
    assert universe(database)["identifiers"] == 2
    known, new = database.written
    assert known["asset_type"] == "common_stock"
    assert known["industry"] == "Semiconductors"
    assert known["listing_metadata"]["source"] == "fixture exchange"
    assert "listing_metadata" not in new and "industry" not in new
