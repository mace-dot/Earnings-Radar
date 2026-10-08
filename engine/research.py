"""Bounded live observations and sampled news/community context."""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any

from engine.options_estimates import chain_estimate
from engine.providers.market import Alpaca
from engine.providers.community import stocktwits
from engine.store import Store
from engine.trade_research import long_options


def market_context(
    store: Store, symbol: str, report_date: str | None = None
) -> dict[str, Any]:
    provider = Alpaca()
    now = datetime.now(timezone.utc)
    response = provider.client.get(
        "https://data.alpaca.markets/v2/stocks/snapshots",
        params={"symbols": symbol, "feed": "iex"},
    )
    response.raise_for_status()
    snapshot = response.json().get(symbol, {})
    trade = snapshot.get("latestTrade", {})
    spot = trade.get("p")
    observed = trade.get("t")
    if not spot or not observed:
        return {"reason": "No current IEX trade observed"}
    store.write(
        "market_observations",
        [
            {
                "id": f"{symbol}:{observed}:iex",
                "symbol": symbol,
                "source": "Alpaca",
                "feed": "iex",
                "observed_at": observed,
                "retrieved_at": now.isoformat(),
                "payload": snapshot,
            }
        ],
    )
    result: dict[str, Any] = {"spot": spot, "spot_as_of": observed, "feed": "iex"}
    try:
        observations = provider.snapshots(symbol)
        values = [o.values for o in observations]
        result["research_trades"] = long_options(
            symbol, spot, values, datetime.now(timezone.utc)
        )
        result["options"] = chain_estimate(
            symbol, spot, values, datetime.now(timezone.utc), report_date
        )
        rows = []
        for item in values:
            from engine.options_estimates import parse_contract

            contract = parse_contract(symbol, item["contract_id"])
            if not contract:
                continue
            rows.append(
                {
                    "id": hashlib.sha256(
                        f"{item['contract_id']}:{now.isoformat()}".encode()
                    ).hexdigest()[:24],
                    "symbol": symbol,
                    "contract_id": contract["contract"],
                    "expiry": contract["expiry"],
                    "strike": contract["strike"],
                    "source": "Alpaca",
                    "feed": "indicative",
                    "as_of": now.isoformat(),
                    "payload": item,
                }
            )
        selected = {
            result["options"].get("call", {}).get("contract"),
            result["options"].get("put", {}).get("contract"),
        }
        selected.update(
            trade["contract"]["contract"]
            for trade in result["research_trades"].values()
        )
        store.write(
            "option_snapshots", [row for row in rows if row["contract_id"] in selected]
        )
    except Exception as exc:
        result["options"] = {"reason": type(exc).__name__, "implied_move": None}
    if result.get("options", {}).get("implied_move") is not None or result.get(
        "research_trades"
    ):
        result["options"]["report_date"] = report_date
        store.write(
            "market_observations",
            [
                {
                    "id": f"{symbol}:{observed}:iex",
                    "symbol": symbol,
                    "source": "Alpaca",
                    "feed": "iex",
                    "observed_at": observed,
                    "retrieved_at": now.isoformat(),
                    "payload": {
                        **snapshot,
                        "option_estimate": result["options"],
                        "research_trades": result.get("research_trades", {}),
                    },
                }
            ],
        )
    return result


def news_context(store: Store, symbol: str) -> dict[str, Any]:
    provider = Alpaca()
    errors = []
    count = 0
    try:
        response = provider.client.get(
            "https://data.alpaca.markets/v1beta1/news",
            params={"symbols": symbol, "limit": 50, "include_content": "false"},
        )
        response.raise_for_status()
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "id": f"alpaca:{item['id']}:{symbol}",
                "symbol": symbol,
                "headline": str(item["headline"])[:1000],
                "url": item["url"],
                "source": item.get("source", "Alpaca news"),
                "published_at": item["created_at"],
                "retrieved_at": now,
                "payload": {"coverage": "bounded_recent_sample"},
            }
            for item in response.json().get("news", [])
            if datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
            >= datetime.now(timezone.utc) - timedelta(days=7)
        ]
        store.write("news_items", rows)
        count = len(rows)
    except Exception as exc:
        errors.append({"provider": "Alpaca news", "reason": type(exc).__name__})
    forums = None
    try:
        rows = stocktwits(symbol)
        store.write("forum_posts", rows)
        forums = len(rows)
    except Exception as exc:
        errors.append({"provider": "Stocktwits", "reason": type(exc).__name__})
    return {
        "sampled_news_count": count,
        "sampled_forum_count": forums,
        "errors": errors,
    }
