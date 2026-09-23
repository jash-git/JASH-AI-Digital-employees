---
name: investigative-research-quantify-and-verify
description: Quantify claims then verify against real data.
version: 1.0.0
author: Hermes Agent
tags: [Research, Fact-check, Verification, Reports, Data]
category: research
---

# Investigative Research: Quantify & Verify

Verify whether an investigation's claims are true — and specifically whether its **numbers/measurable facts** are *actually credible*. The universal trap: verifying the person/story is real but leaving the numbers assumed. You must quantify every claim, then verify against REAL data before declaring anything credible.

## Core Principle (applies to ALL research, not just finance)
**Quantify first, then verify against real data before declaring anything credible.**
Turn every qualitative claim into a concrete number, then pull actual data to check it — rather than trusting the source's self-reported figure. "It sounds plausible" is not verification.

## When to Use
- User shares a news article or topic and asks "is this true?" / "可信嗎".
- The story hinges on a number or measurable fact (annual dividend, portfolio value, years to reach X, revenue, growth %, benchmark result, historical date, survey stat).
- Any deliverable where the reader will want to check your work.

## Procedure

### 1. Extract & enumerate every claim
Read the full text (web_extract → fallback browser/`curl`). Pull EVERY numeric/measurable claim into a table: timeline of events + figures (year → event → amount). Separate "story facts" (person, book, dates) from "quantitative claims" (returns, totals, rates).

### 2. Verify the *story* is real (person/book/sources)
Confirm the subject, book, social account, and multi-source coverage exist (search listings; find ≥1 independent outlet reprinting it). Flag self-reported figures as "自報 / not audited."

### 3. Build a quantitative model of the core claim
Reconstruct the path with formulas:
- Compounding: FV = PMT × [((1+r)ⁿ − 1)/r]; CAGR = (end/start)^(1/years) − 1.
- Or whatever math fits the claim (growth %, ratios, totals).
Estimate realistic ranges from first principles (e.g. subject's income → realistic savings rate).

### 4. VERIFY key assumptions against REAL data ← THE KEY STEP
Do NOT assume a number is plausible — prove it. Pull actual data for the relevant market/index/subject:
- Taiwan markets: `^TWII` (加權報酬指數, includes dividends) beats plain TAIEX; fetch daily closes from Yahoo Finance API (`query1.finance.yahoo.com/v8/finance/chart/%5ETWII`) and compute CAGR per period. Check key stocks separately (e.g. `2330.TW`).
- General: use real APIs, official stats, primary sources — not the article's own numbers or third-party estimates.
Compare the story's implied figure to what reality actually delivered in those exact conditions. Note if it required picking winners (concentration) vs. broad average.

### 5. Reverse-calculate "what would it take?"
Answer: given realistic inputs, what output is needed? Given a target, what input is required? This exposes whether the story needs luck/concentration/high-effort or just happened — and where the optimism lives.

### 6. Assess plausibility + flag risks
Score each claim (★ scale): person真实性 / narrative coherence / number precision / replicability. List risks: survivorship bias, "assumed rate not guaranteed", "metric ≠ actual result", concentration risk, unaudited self-reported figures.

## Deliverable (make it COMPLETE — don't wait to be asked)
A report that includes ALL of:
- Original claims table + verification results per claim (real data vs. claimed).
- The quantitative model + reverse-calculation tables.
- **Charts** for the data-heavy parts (SVG-in-HTML bar/column charts work well).
- **References/sources appendix** with URLs (register sources at retrieval time; don't reconstruct from memory — see `grounded-citations`).
- Convert to **PDF** when data-heavy: write HTML → `libreoffice --headless --convert-to pdf`.

## User preference notes
- Clean report style: references at the end, NOT Perplexity-style inline `[1][2]` markers. (`grounded-citations` skill exists but its inline style is heavier than this user wants for reports.)
- Verify numbers against real data up front — the single most common gap is assuming a figure instead of proving it.

## Support files
- `references/taiwan-market-verification.md` — full recipe + knowledge bank for verifying wealth/compounding claims against real Taiwanese market data (Yahoo Finance API fetch, CAGR math, report-completeness preference). Reuse the pattern for any market where a daily-close API exists.

## Pitfalls
- Verifying the *person* but not the *math* → story looks true, claim may be optimistic.
- Assuming a number (e.g. "12–14%/year") without checking what reality actually delivered in those conditions.
- Listing sources from memory at the end instead of registering them as you retrieve.
- Delivering a text-only report for data-heavy claims (missing charts/PDF).
- Treating this as finance-only — it applies to ANY investigation with measurable claims.
