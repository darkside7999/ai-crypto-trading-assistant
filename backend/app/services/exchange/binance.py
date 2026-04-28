from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

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
        secret = self._testnet_secret(settings)
        if settings.binance_testnet_api_key and secret:
            self.exchange.apiKey = settings.binance_testnet_api_key
            self.exchange.secret = secret

    def _testnet_secret(self, settings) -> str | None:
        if settings.binance_testnet_key_type.lower() == "ed25519":
            return self._load_private_key(settings.binance_testnet_private_key, settings.binance_testnet_private_key_path)
        return settings.binance_testnet_secret

    def _load_private_key(self, value: str | None, path: str | None) -> str | None:
        if value:
            return value.replace("\\n", "\n")
        if path:
            key_path = Path(path).expanduser()
            if key_path.exists():
                return key_path.read_text(encoding="utf-8")
        return None

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


class CcxtPublicMarketData:
    def __init__(self, exchange_id: str) -> None:
        import ccxt

        exchange_class = getattr(ccxt, exchange_id)
        self.exchange_id = exchange_id
        self.exchange = exchange_class({"enableRateLimit": True})
        self.exchange.load_markets()

    def _supported_symbols(self, symbols: list[str]) -> list[str]:
        return [symbol for symbol in symbols if symbol in self.exchange.markets]

    def fetch_tickers(self, symbols: list[str]) -> list[MarketTicker]:
        supported = self._supported_symbols(symbols)
        if not supported:
            return []
        raw = self.exchange.fetch_tickers(supported)
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
                    quote_volume=float(data.get("quoteVolume") or data.get("baseVolume") or 0),
                    percentage=float(data.get("percentage") or 0),
                )
            )
        return tickers

    def fetch_ohlcv(self, symbol: str, timeframe: str = "5m", limit: int = 50) -> list[dict[str, float | str]]:
        if symbol not in self.exchange.markets:
            raise ValueError(f"{symbol} is not available on {self.exchange_id}")
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


def get_market_data_client():
    from app.config import get_settings

    provider = get_settings().market_data_provider
    if provider == "binance_public":
        return CcxtPublicMarketData("binance")
    if provider == "kraken_public":
        return CcxtPublicMarketData("kraken")
    if provider == "okx_public":
        return CcxtPublicMarketData("okx")
    if provider == "binance_testnet":
        return BinanceMarketData()
    return CcxtPublicMarketData("kraken")
