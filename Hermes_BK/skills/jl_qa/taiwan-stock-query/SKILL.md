---
name: taiwan-stock-query
description: Query Taiwan stock/ETF prices, opening prices, and market data via Yahoo Finance API, TWSE API, or browser.
---

# Taiwan Stock Query

Query real-time or delayed stock/ETF data for Taiwan securities (台積電, 0050, etc.).

## Primary Approach: Yahoo Finance API

Yahoo Finance provides reliable Taiwan stock data via their v8 chart endpoint.

**Steps:**

1. Call `curl -s "https://query1.finance.yahoo.com/v8/finance/chart/<TICKER>.TW?range=1d&interval=1d"` (e.g., `0050.TW`, `2330.TW`)
2. Parse JSON response for `meta` object fields:
   - `regularMarketOpen` — opening price
   - `regularMarketPrice` — current/latest price
   - `regularMarketDayHigh` / `regularMarketDayLow` — intraday range
   - `shortName` — fund/stock name
   - `currency` — usually TWD
3. Extract values with `python3 -c` or `jq`.

**Example command:**
```bash
curl -s "https://query1.finance.yahoo.com/v8/finance/chart/0050.TW?range=1d&interval=1d" | python3 -c "
import sys, json
data = json.load(sys.stdin)
meta = data['chart']['result'][0]['meta']
print('Open:', meta['regularMarketOpen'])
print('Price:', meta['regularMarketPrice'])
print('Name:', meta['shortName'])
"
```

> **Note:** If `query1` fails, try `query2.finance.yahoo.com` or `query2.finance.yahoo.com/v10/finance/quoteSummary/<TICKER>.TW?modules=price`.

## Browser Fallback: Yahoo Finance Web Page

When API calls fail (DNS, rate limiting, bot detection):

1. Navigate to `https://finance.yahoo.com/quote/<TICKER>.TW/`
2. Use `browser_snapshot` to extract data from the page
3. Look for the "Open", "Previous Close", "Day's Range" fields in the summary section.

## TWSE API (Often Unavailable)

The Taiwan Stock Exchange API (`https://api.twse.io.tw/v1/exchange/ETF/ETF_<code>.json`) may be unreachable from some environments due to DNS resolution failures.

**If reachable:**
```bash
curl -s "https://api.twse.io.tw/v1/exchange/ETF/ETF_<code>.json" | python3 -c "..."
```
Columns: fund code, name, date, open, high, low, close, volume.

**Pitfall:** If `nslookup twse.io.tw` returns NXDOMAIN, the API is unreachable from this network — skip to Yahoo Finance approach.

## Dividend History (annual cash dividend per unit/share)

For feasibility/analysis tasks, you need each security's **year-by-year dividends** + current price. Reliable sources:

1. **FinLab** (`finlab.finance`) — has a clean annual table on `/stocks/<CODE>/dividend`. It is server-rendered enough to curl (unlike wantgoo/goodinfo which are Cloudflare/JS). Extract the `年度配息合計` block + current price line (`以 YYYY-MM-DD 收盤 XX 元計`).
   ```bash
   timeout 25 curl -s "https://finlab.finance/stocks/0056/dividend" > f.html
   python3 -c "import re,html;t=open('f.html',encoding='utf-8',errors='ignore').read();t=re.sub(r'<script.*?</script>','',t,flags=re.S);t=re.sub(r'<style.*?</style>','',t,flags=re.S);t=re.sub(r'<[^>]+>',' ',t);s=html.unescape(t);i=s.find('年度配息合計');print(s[i:i+1200])"
   ```
   Returns: annual table (year / times / total 元) + per-ex-dividend detail + current price.
2. **Yahoo股市** (`tw.stock.yahoo.com/quote/<CODE>.TW/dividend`) — server-rendered, has `歷年股利分配` with annual totals (e.g. TSMC 2330). Same curl+python strip works. Avoid wantgoo/goodinfo/pocket/histock/goodinfo — all Cloudflare "Just a moment" or JS-only.
3. **Business Weekly / Money101** blog posts often summarize yearly dividends in prose (search `CODE + 每年配息 + year list`).

Then compute dividend yield = annual_div ÷ current_price × 100%. For feasibility, reverse-engineer implied portfolio value = reported_dividend ÷ assumed_yield.

## Weather Queries

For weather, use `curl -s "https://wttr.in/<city>?format=%c+%t+%h+%w"` — returns emoji, temperature, humidity, wind in one line.
