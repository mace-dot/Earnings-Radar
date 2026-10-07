"""Provider contracts preserve availability and provenance."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True)
class Observation:
    symbol: str
    observed_at: datetime
    available_at: datetime
    source: str
    values: dict[str, Any]
    feed: str = "official"

    def at(self, as_of: datetime) -> dict[str, Any]:
        if self.available_at > as_of or self.observed_at > as_of:
            raise ValueError("Observation was unavailable at the decision cutoff")
        return self.values


class EarningsCalendarProvider(Protocol):
    def calendar(self, start: str, end: str) -> list[Observation]: ...


class PriceProvider(Protocol):
    def bars(self, symbols: list[str], start: str, end: str) -> list[Observation]: ...


class OptionsProvider(Protocol):
    def snapshots(self, symbol: str) -> list[Observation]: ...


class EstimatesProvider(Protocol):
    def estimates(self, symbol: str) -> list[Observation]: ...


class NewsProvider(Protocol):
    def news(self, symbol: str) -> list[Observation]: ...


class FundamentalsProvider(Protocol):
    def fundamentals(self, cik: str) -> dict[str, Any]: ...
