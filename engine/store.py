"""Bounded server-only Supabase client. Never logs credentials or provider bodies."""

import os
import re
from typing import Any

import httpx

TABLES = {
    "securities",
    "earnings_events",
    "daily_bars",
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
}


class Store:
    def __init__(self) -> None:
        self.url = os.environ.get("SUPABASE_URL", "").rstrip("/")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
        if (
            not re.fullmatch(r"https://[a-z0-9-]+\.supabase\.co", self.url)
            or not self.key
        ):
            raise RuntimeError("Supabase server configuration missing")
        headers = {"apikey": self.key, "Content-Type": "application/json"}
        if not self.key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {self.key}"
        self.client = httpx.Client(timeout=45, headers=headers)

    def read(
        self, table: str, params: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        return self._request(table, params=params or {"select": "*", "limit": "1000"})

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
