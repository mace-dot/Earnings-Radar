from datetime import date

from engine.providers.market import Finnhub, calendar_chunks


def test_calendar_chunks_cover_the_near_dates_and_the_far_dates():
    chunks = calendar_chunks("2026-10-09", "2026-10-24")
    assert chunks[0] == ("2026-10-09", "2026-10-15")
    assert chunks[-1][1] == "2026-10-24"
    assert all(
        date.fromisoformat(end) >= date.fromisoformat(start) for start, end in chunks
    )


class Response:
    def __init__(self, symbols):
        self.symbols = symbols

    def raise_for_status(self):
        return None

    def json(self):
        return {
            "earningsCalendar": [
                {"symbol": symbol, "date": "2026-10-12", "hour": "amc"}
                for symbol in self.symbols
            ]
        }


class Client:
    def __init__(self):
        self.calls = []

    def get(self, url, params):
        self.calls.append(params)
        symbol = "NEAR" if params["from"] == "2026-10-09" else "LATER"
        return Response([symbol])


def test_finnhub_calendar_requests_short_windows():
    provider = Finnhub.__new__(Finnhub)
    provider.client = Client()
    rows = provider.calendar("2026-10-09", "2026-10-20")
    assert [call["from"] for call in provider.client.calls] == [
        "2026-10-09",
        "2026-10-16",
    ]
    assert {row.symbol for row in rows} == {"NEAR", "LATER"}
