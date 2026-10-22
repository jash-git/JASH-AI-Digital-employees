# Free Market Data API — Interval & Limit Matrix

Re-probe before relying on this. Free tiers and supported intervals change; the "verify live" rule in SKILL.md always wins over this table.

## Forex (e.g. EURUSD)
| Provider | Key? | 3-min support | Standard intervals | Free-tier limit | Notes |
|---|---|---|---|---|---|
| OANDA v20 | Account + token | ✅ `bar_size=M3` | M1,M3,...,D | ~120 req/min; bar history capped | Real interbank quotes; best quality for backtest |
| Twelve Data | Free signup key | ✅ `interval=3_min` | 1min…1day | ~800 req/day, 8/min | Easiest code; JSON/Socket |
| MetaTrader5 | Broker account | ✅ `PERIOD_M3` | any M1–M240+ | broker-dependent | Pulls from broker ticks; arbitrary custom periods |
| Yahoo / yfinance | None | ❌ (no 3m) | 1m,2m,5m,15m,30m,60m,90m,1h | ~rate-limited, no key | Forex symbol `EURUSD=X`; intraday ≤ last 60 days |
| biquote.io | None | ❌ (400 on 3min) | 1m,5m,15m,30m,1h,4h,1d | ~15k req/min | No key; CFD quotes (`volume` always 0 for FX) |

## Crypto / Stocks (general)
- **Coinbase / Kraken / Binance public**: no key for basic OHLC; support custom minute intervals incl. 3-min on most pairs.
- **Alpha Vantage**: `FX_INTRADAY`/`TIME_SERIES_INTRADAY`; free key but very low cap (~25 req/day now); standard intervals only (no 3-min).
- **Twelve Data / Finnhub / IEX**: check per-interval; Finnhub forex candle needs paid on free tier.

## Verification snippet (Python, no-key provider)
```python
import requests
for iv in ["3min", "1m", "5m"]:
    try:
        r = requests.get("https://biquote.io/api/EURUSD/ohlc",
                         params={"interval": iv, "limit": 3}, timeout=15)
        bars = r.json().get("bars") or []
        print(iv, r.status_code, len(bars))   # 400 => not supported
    except Exception as e:
        print(iv, "ERROR", type(e).__name__, e)
```
Probe the exact interval first; a 400 (or empty bars) means that provider can't serve it regardless of what its docs claim.
