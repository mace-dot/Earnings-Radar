"""Bounded server-only Supabase client. Never logs credentials or provider bodies."""

import os
import re
from typing import Any

import httpx

TABLES = {
    "securities",
    "earnings_events",
    "daily_bars",
    "market_history_days",
    "validation_cases",
    "validation_outcomes",
    "option_snapshots",
    "estimate_revisions",
    "news_items",
    "features",
    "lines",
    "line_sides",
    "picks",
    "pick_outcomes",
    "model_registry",
    "model_portfolio_trades",
    "engine_runs",
    "score_queue",
    "market_observations",
    "forum_posts",
    "market_coverage",
    "market_coverage_summary",
    "current_line_symbols",
    "latest_price_features",
}


class ConfigurationError(RuntimeError):
    """Actionable configuration failure whose message contains no secret values."""


def database_configuration() -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL", "").strip().rstrip("/")
    key = (
        os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        or os.environ.get("SUPABASE_SECRET_KEY", "").strip()
    )
    if not url:
        raise ConfigurationError("SUPABASE_URL is missing in this worker environment")
    if not re.fullmatch(r"https://[a-z0-9-]+\.supabase\.co", url):
        raise ConfigurationError(
            "SUPABASE_URL must be the project API URL, not a dashboard or database URL"
        )
    if not key:
        raise ConfigurationError(
            "SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_SECRET_KEY) is missing in this worker environment"
        )
    if key.startswith("sbp_"):
        raise ConfigurationError(
            "A Supabase personal access token cannot authenticate database requests; use a server API key"
        )
    if key.startswith("sb_publishable_"):
        raise ConfigurationError(
            "Use a Supabase server secret key, not a publishable key"
        )
    return url, key


class Store:
    def __init__(self) -> None:
        self.url, self.key = database_configuration()
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        if not self.key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self.key}"
        self.client = httpx.Client(timeout=45, headers=headers)

    def read(
        self, table: str, params: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        return self._request(table, params=params or {"select": "*", "limit": "1000"})

    def pages(
        self, table: str, params: dict[str, str], capacity: int = 20000
    ) -> list[dict[str, Any]]:
        output = []
        for offset in range(0, capacity, 1000):
            rows = self.read(table, {**params, "limit": "1000", "offset": str(offset)})
            output.extend(rows)
            if len(rows) < 1000:
                return output
        raise RuntimeError("Pagination exceeded capacity; do not silently truncate")

    def write(
        self,
        table: str,
        rows: list[dict[str, Any]],
        conflict: str = "id",
        immutable: bool = False,
    ) -> None:
        if not rows:
            return
        preference = "ignore-duplicates" if immutable else "merge-duplicates"
        self._request(
            table,
            method="POST",
            params={"on_conflict": conflict},
            json=rows,
            headers={"Prefer": f"resolution={preference},return=minimal"},
        )

    def _request(self, table: str, method: str = "GET", **kwargs: Any) -> Any:
        if table not in TABLES:
            raise ValueError("Unknown table")
        response = self.client.request(method, f"{self.url}/rest/v1/{table}", **kwargs)
        if not response.is_success:
            raise RuntimeError(f"Database operation failed ({response.status_code})")
        return response.json() if response.content else []

    def rpc(self, name: str, payload: dict[str, Any]) -> Any:
        if name not in {
            "radar_request_score",
            "radar_claim_scores",
            "radar_claim_market",
            "radar_history_bars",
            "radar_history_packs",
        }:
            raise ValueError("Unknown RPC")
        if name == "radar_history_bars":
            output = []
            for offset in range(0, 50000, 1000):
                response = self.client.post(
                    f"{self.url}/rest/v1/rpc/{name}",
                    json=payload,
                    params={
                        "limit": "1000",
                        "offset": str(offset),
                        "order": "symbol.asc,session_date.asc",
                    },
                )
                if not response.is_success:
                    raise RuntimeError(
                        f"Queue operation failed ({response.status_code})"
                    )
                rows = response.json()
                output.extend(rows)
                if len(rows) < 1000:
                    return output
            raise RuntimeError(
                "History RPC exceeded capacity; do not silently truncate"
            )
        response = self.client.post(f"{self.url}/rest/v1/rpc/{name}", json=payload)
        if not response.is_success:
            raise RuntimeError(f"Queue operation failed ({response.status_code})")
        return response.json()

    def finish_market(
        self, symbol: str, lease_token: str, payload: dict[str, Any]
    ) -> bool:
        rows = self._request(
            "market_coverage",
            method="PATCH",
            params={"symbol": f"eq.{symbol}", "lease_token": f"eq.{lease_token}"},
            json=payload,
            headers={"Prefer": "return=representation"},
        )
        return bool(rows)

    def finish_score(self, symbol: str, reason: str | None = None) -> None:
        from datetime import datetime, timezone

        self._request(
            "score_queue",
            method="PATCH",
            params={"symbol": f"eq.{symbol}"},
            json={
                "state": "failed" if reason else "completed",
                "reason": reason,
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "leased_until": None,
            },
        )
