---
name: market-data-apis
description: Pick & verify free OHLC candlestick APIs incl. 3-min bars.
category: finance
---

# Free Market Data APIs for Candlesticks

Use when the user wants OHLC / K-line data from a free or public market-data API — especially when a **specific non-standard interval** (e.g. 3-minute) is required, or when choosing among several "free" providers.

## Golden rule: verify the requested interval live before recommending
Marketing copy and docs routinely claim support that isn't actually wired up. A provider can silently reject an odd interval with `HTTP 400` while happily serving its standard ones (`1m`, `5m`, `15m`). **Probe the exact interval the user asked for against the real endpoint before naming a provider as working.** Do not trust the interval list in READMEs or landing pages.

Why: an API that returns 400 (or silently resamples/truncates) on the requested interval is useless even if its docs say it supports it. A live probe costs one call and prevents recommending a dead end.

## Procedure
1. List candidate free providers for the asset class (forex/crypto/stocks).
2. For each, hit the real OHLC endpoint with the **exact** `interval` requested and a small `limit`. Confirm HTTP 200 + sane OHLC rows.
3. Empirically confirm key/signup requirement and rate-limit headroom (note the free-tier cap you observed).
4. Recommend only providers that passed step 2–3, ordered by quality vs. setup cost. State the verified limits so the user isn't surprised.

## Known gaps (verified — still re-check before relying)
- **Yahoo / yfinance**: intraday interval set is `1m,2m,5m,15m,30m,60m,90m,1h,...` — **no 3-minute**. Forex via `<PAIR>=X` (e.g. `EURUSD=X`). Do not offer this for a 3-min request.
- **biquote.io**: no key needed; OHLC intervals are `1m,5m,15m,30m,1h,4h,1d` — **no 3-minute** (returns HTTP 400 on `3min`/`3m`). ~15k req/min free.
- Reliable free paths that DO do 3-min: **OANDA v20** (`bar_size=M3`, needs free account/token, best-quality interbank quotes), **Twelve Data** (`interval=3_min`, free key ~800 req/day), **MetaTrader5** (`PERIOD_M3`, needs a broker account, any custom period from broker ticks).

Full provider matrix (intervals, key requirement, limits) lives in `references/free-api-intervals.md`. Re-probe before trusting it — free tiers change.

## Output style for this user
- Answer in 繁體中文.
- Lead with a short verdict table (provider |免key?|3min支援?|限制), then the one-line recommendation, then copy-paste code for the chosen provider. Keep prose minimal; the user dislikes over-explanation.