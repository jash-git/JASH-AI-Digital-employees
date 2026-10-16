---
name: web-tools-keyless-setup
description: "web_extract 無 key：extract_backend 設 parallel(匿名免費）"
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [web, search, extract, keyless, parallel, no-api-key]
    category: devops
---

# Web Tools Without API Keys (Keyless)

## When to Use This
Use when Hermes `web_search` works but `web_extract` fails with:
> DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content. Set web.extract_backend to firecrawl, tavily, keenable, exa, or parallel.

This means the extract backend inherited the search backend (ddgs), which can only search, not fetch page bodies. No API key required — use the keyless free tier.

## The Fix
Set the extract backend to `parallel`, which supports a **keyless anonymous free tier** (`KEYLESS = True`). Without `PARALLEL_API_KEY` it auto-runs the keyless ring (exa → parallel → firecrawl → keenable round-robin), so it works with zero keys. Keep search on ddgs (fast, already fine).

```bash
hermes config set web.extract_backend parallel
```

Verify:
```bash
hermes config get web.extract_backend   # → parallel
```

Then `web_extract` fetches page bodies directly. Verified 2026-10-16 on winvest.tw article.

## Notes
- Keyless free tiers are rate-limited — under burst load expect occasional failures or slowness; a real API key gives guaranteed throughput if you ever need it.
- `hermes config set` routes dotted keys to config.yaml (never hand-edit). Per-profile configs live at ~/.hermes/profiles/<name>/config.yaml and must be edited separately when that profile is active.
- Tool/backend changes take effect on /reset or a new process — not mid-conversation.
