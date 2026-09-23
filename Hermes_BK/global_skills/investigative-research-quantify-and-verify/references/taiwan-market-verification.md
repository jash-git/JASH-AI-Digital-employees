# Taiwan Market Verification — Session Knowledge Bank

Condensed, reusable recipe for verifying a wealth/compounding claim against
**real** Taiwanese market data (proven from the 流浪教師存股 investigation,
2026-08-28). The core lesson: do NOT assume a return rate like "12–14%/year" is
plausible — pull actual historical closes and compute CAGR per period.

## Why ^TWII (not plain TAIEX)
`^TWII` = Taiwan Weighted **Total Return** Index. It folds dividends back into
the index, so it reflects what a long-term stock-saver actually earns. Plain
TAIEX drops dividends on each ex-dividend day and understates total return.
For a "存股" (accumulate-shares) story, `^TWII` is the right benchmark.

## Fetch daily closes from Yahoo Finance API
```bash
# Total-return index (^TWII). Note %5E encodes the ^ character.
curl -sL --max-time 30 -H "User-Agent: Mozilla/5.0" \
  "https://query1.finance.yahoo.com/v8/finance/chart/%5ETWII?period1=1098748800&period2=1786464000&interval=1d" \
  -o twii.json

# A single stock, e.g. TSMC (2330.TW)
curl -sL --max-time 30 -H "User-Agent: Mozilla/5.0" \
  "https://query1.finance.yahoo.com/v8/finance/chart/2330.TW?period1=1098748800&period2=1786464000&interval=1d" \
  -o tcecc.json
```
- `period1`/`period2` are Unix seconds. Use a wide range; the chart endpoint
  returns every daily bar in that window (5,000+ points is normal).
- **Rate limit:** Yahoo may return HTTP 429 on rapid successive calls. Retry with
  a fresh `User-Agent` header or wait ~1s between symbols. If `%5ETWII` fails,
  try `query2.finance.yahoo.com`.
- The JSON path is `chart.result[0].timestamp[]` (unix seconds) and
  `chart.result[0].indicators.quote[0].close[]`.

## Compute CAGR per period (Python, stdlib only)
```python
import json, datetime
d = json.load(open('twii.json'))
r = d['chart']['result'][0]
pts = [(t, c) for t, c in zip(r['timestamp'], r['indicators']['quote'][0]['close']) if c]

def close_on_or_before(year, month=12, day=31):
    tgt = datetime.datetime(year, month, day).timestamp()
    best, bd = None, 9e9
    for t, c in pts:
        dt = abs(t - tgt)
        if dt < bd and t <= tgt + 86400*5:   # allow a few days into next year
            bd, best = dt, (t, c)
    return best[1]

def close_on_or_after(year, month=1, day=1):
    tgt = datetime.datetime(year, month, day).timestamp()
    best, bd = None, 9e9
    for t, c in pts:
        if abs(t - tgt) < bd: bd, best = abs(t-tgt), (t, c)
    return best[1]

def cagr(start, end, years):
    return (end/start)**(1/years) - 1
```
Then compute CAGR for each story-relevant window and compare to the claim's
implied rate. Example real results from the investigation:

| Period | ^TWII CAGR (total return) | TSMC CAGR |
|---|---|---|
| 2004 → 2016 | ~4.2%/yr | ~14.1%/yr |
| 2016 → 2026 | ~17.2%/yr | ~29.4%/yr |

**Interpretation pattern:** a story that needs "12–14%/yr" may be achievable only
if the subject concentrated in winners (TSMC) rather than holding the broad index
(only ~4% in 2004–2016). Note whether the claim required picking winners vs. the
broad average — this is where "optimism" usually lives.

## Compounding math used to reverse-engineer a claim
- Annual fixed contribution (year-end, start=0):
  `FV = PMT * ((1+r)^n - 1) / r`
- CAGR: `(end/start)^(1/years) - 1`
- To find "how much must be saved per year to hit target X": solve the FV formula
  for PMT. To find "what return is needed given fixed savings": numerically root-
  search r (bisection on [0, 0.40] converges in ~200 iters).

## Report-completeness preference (this user)
A data-heavy financial/news investigation report should proactively include — not
wait to be asked for:
1. A **references/sources appendix** with URLs at the end (clean style, NOT
   Perplexity-style inline `[1][2]` markers — see `grounded-citations`).
2. **Charts / visualizations** for the numeric comparisons (SVG-in-HTML bar/column
   charts render crisply).
3. A **PDF export** when data-heavy: write HTML → `libreoffice --headless --convert-to pdf`.

## Pitfalls found this session
- Yahoo Finance API returns HTTP 429 under load — retry with a User-Agent header,
  don't treat it as "the endpoint is broken."
- The chart JSON's `close[]` has `null` entries (ex-dividend gaps); filter them
  before zipping timestamps to prices.
- Don't reconstruct the sources list from memory at the end — register URLs as you
  retrieve them (see `grounded-citations`).
