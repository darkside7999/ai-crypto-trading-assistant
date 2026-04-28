from datetime import datetime, timezone
from urllib.parse import urlparse
from xml.etree import ElementTree

import httpx

from app.config import get_settings
from app.services.exchange.binance import BinanceMarketData


ALLOWED_RSS_HOSTS = {
    "www.coindesk.com",
    "coindesk.com",
    "cointelegraph.com",
    "www.cointelegraph.com",
    "cryptopanic.com",
    "www.cryptopanic.com",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_rss_urls() -> list[str]:
    urls: list[str] = []
    for url in get_settings().market_intel_rss_url_list:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            continue
        if parsed.hostname not in ALLOWED_RSS_HOSTS:
            continue
        urls.append(url)
    return urls


class MarketIntelService:
    def collect(self, symbols: list[str], include_ohlcv: bool = True) -> dict:
        settings = get_settings()
        market = BinanceMarketData()
        tickers = market.fetch_tickers(symbols)
        ticker_payload = [
            {
                "symbol": ticker.symbol,
                "last": ticker.last,
                "bid": ticker.bid,
                "ask": ticker.ask,
                "spread_pct": ticker.spread_pct,
                "quote_volume": ticker.quote_volume,
                "change_24h_pct": ticker.percentage,
            }
            for ticker in tickers
        ]

        ohlcv_payload = {}
        if include_ohlcv:
            for symbol in symbols:
                try:
                    ohlcv_payload[symbol] = market.fetch_ohlcv(symbol)
                except Exception as exc:
                    ohlcv_payload[symbol] = {"error": str(exc)}

        payload = {
            "generated_at": _now(),
            "sources": [
                {"name": "Binance via CCXT", "type": "exchange", "url": "https://www.binance.com", "generated_at": _now()}
            ],
            "tickers": ticker_payload,
            "ohlcv": ohlcv_payload,
            "coingecko": None,
            "rss": [],
        }

        if settings.market_intel_enable_coingecko:
            payload["coingecko"] = self._coingecko_global()

        payload["rss"] = self._rss_items()
        return payload

    def _coingecko_global(self) -> dict | None:
        url = "https://api.coingecko.com/api/v3/global"
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                response.raise_for_status()
            data = response.json().get("data", {})
            return {
                "source": {"name": "CoinGecko global", "url": url, "generated_at": _now()},
                "market_cap_change_24h_pct": data.get("market_cap_change_percentage_24h_usd"),
                "btc_dominance_pct": (data.get("market_cap_percentage") or {}).get("btc"),
                "eth_dominance_pct": (data.get("market_cap_percentage") or {}).get("eth"),
            }
        except Exception as exc:
            return {"source": {"name": "CoinGecko global", "url": url}, "error": str(exc)}

    def _rss_items(self) -> list[dict]:
        items: list[dict] = []
        for url in _safe_rss_urls():
            try:
                with httpx.Client(timeout=10) as client:
                    response = client.get(url)
                    response.raise_for_status()
                root = ElementTree.fromstring(response.text)
                for item in root.findall(".//item")[:5]:
                    items.append(
                        {
                            "source_url": url,
                            "title": (item.findtext("title") or "").strip()[:240],
                            "link": (item.findtext("link") or "").strip(),
                            "published": (item.findtext("pubDate") or "").strip(),
                        }
                    )
            except Exception as exc:
                items.append({"source_url": url, "error": str(exc)})
        return items
