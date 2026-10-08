from engine.providers.listings import classify


def test_exchange_name_classification_is_conservative():
    base = {"ETF": "N", "Test Issue": "N"}
    assert classify({**base, "Security Name": "Fixture Common Stock"}) == "common_stock"
    assert (
        classify({**base, "Security Name": "Warrants to purchase common stock"})
        == "warrant"
    )
    assert classify({**base, "Security Name": "Preferred Stock"}) == "preferred"
    assert (
        classify({**base, "Security Name": "American Depositary Shares"})
        == "depositary_security"
    )
    assert classify({**base, "Security Name": "Fixture"}) == "listed_unclassified"
    assert classify({**base, "ETF": "Y", "Security Name": "Common Stock ETF"}) == "fund"
