"""Bounded live observations and sampled news/community context."""

import hashlib
from datetime import datetime, timezone, timedelta
from typing import Any

from engine.options_estimates import chain_estimate
from engine.providers.market import Finnhub
from engine.providers.public_market import Cboe
from engine.providers.community import stocktwits
from engine.store import Store
from engine.trade_research import long_options


def market_context(
    store: Store, symbol: str, report_date: str | None = None
) -> dict[str, Any]:
    provider = Cboe()
    now = datetime.now(timezone.utc)
    trade = Finnhub().quote(symbol)
    snapshot = {"latestTrade": trade, "price_source": "Finnhub"}
    spot, observed = trade["p"], trade["t"]
    store.write(
        "market_observations",
        [
            {
                "id": f"{symbol}:{observed}:finnhub",
                "symbol": symbol,
                "source": "Finnhub",
                "feed": "finnhub_free",
                "observed_at": observed,
                "retrieved_at": now.isoformat(),
                "payload": snapshot,
            }
        ],
    )
    result: dict[str, Any] = {
        "spot": spot,
        "spot_as_of": observed,
        "feed": "finnhub_free",
    }
    try:
        observations = provider.snapshots(symbol)
        values = [o.values for o in observations]
        result["research_trades"] = long_options(
            symbol, spot, values, datetime.now(timezone.utc)
        )
        result["options"] = chain_estimate(
            symbol, spot, values, datetime.now(timezone.utc), report_date
        )
        result["options"].update(
            {
                "source": "Cboe delayed snapshot",
                "quote_kind": "Delayed snapshot estimate; individual quote age unknown",
            }
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
                    "source": "Cboe",
                    "feed": "cboe_delayed",
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
                    "id": f"{symbol}:{observed}:finnhub",
                    "symbol": symbol,
                    "source": "Finnhub",
                    "feed": "finnhub_free",
                    "observed_at": observed,
                    "retrieved_at": now.isoformat(),
                    "payload": {
                        **snapshot,
                        "option_estimate": result["options"],
                        "research_trades": result.get("research_trades", {}),
                        "research_retrieved_at": now.isoformat(),
                    },
                }
            ],
        )
    return result


def news_context(store: Store, symbol: str) -> dict[str, Any]:
    provider = Finnhub()
    errors = []
    count = 0
    try:
        response = provider.client.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": symbol,
                "from": (datetime.now(timezone.utc) - timedelta(days=7))
                .date()
                .isoformat(),
                "to": datetime.now(timezone.utc).date().isoformat(),
            },
        )
        response.raise_for_status()
        now = datetime.now(timezone.utc).isoformat()
        rows = [
            {
                "id": f"finnhub:{item['id']}:{symbol}",
                "symbol": symbol,
                "headline": str(item["headline"])[:1000],
                "url": item["url"],
                "source": item.get("source", "Finnhub news"),
                "published_at": datetime.fromtimestamp(
                    item["datetime"], timezone.utc
                ).isoformat(),
                "retrieved_at": now,
                "payload": {"coverage": "bounded_recent_sample"},
            }
            for item in response.json()[:50]
            if datetime.fromtimestamp(item["datetime"], timezone.utc)
            >= datetime.now(timezone.utc) - timedelta(days=7)
        ]
        store.write("news_items", rows)
        count = len(rows)
    except Exception as exc:
        errors.append({"provider": "Finnhub news", "reason": type(exc).__name__})
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
