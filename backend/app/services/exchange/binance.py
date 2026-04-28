from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import get_settings


@dataclass
class MarketTicker:
    symbol: str
    last: float
    bid: float
    ask: float
    quote_volume: float
    percentage: float

    @property
    def spread_pct(self) -> float:
        if not self.bid or not self.ask:
            return 999.0
        mid = (self.bid + self.ask) / 2
        return ((self.ask - self.bid) / mid) * 100 if mid else 999.0


class BinanceMarketData:
    def __init__(self) -> None:
        settings = get_settings()
        import ccxt

        self.exchange = ccxt.binance({"enableRateLimit": True})
        self.exchange.set_sandbox_mode(True)
        if settings.binance_testnet_api_key and settings.binance_testnet_secret:
            self.exchange.apiKey = settings.binance_testnet_api_key
            self.exchange.secret = settings.binance_testnet_secret

    def fetch_tickers(self, symbols: list[str]) -> list[MarketTicker]:
        raw = self.exchange.fetch_tickers(symbols)
        tickers: list[MarketTicker] = []
        for symbol, data in raw.items():
            last = float(data.get("last") or 0)
            bid = float(data.get("bid") or last or 0)
            ask = float(data.get("ask") or last or 0)
            tickers.append(
                MarketTicker(
                    symbol=symbol,
                    last=last,
                    bid=bid,
                    ask=ask,
                    quote_volume=float(data.get("quoteVolume") or 0),
                    percentage=float(data.get("percentage") or 0),
                )
            )
        return tickers

    def fetch_ohlcv(self, symbol: str, timeframe: str = "5m", limit: int = 50) -> list[dict[str, float | str]]:
        candles = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        return [
            {
                "timestamp": datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).isoformat(),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }
            for row in candles
        ]
