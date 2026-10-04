---
name: skill-audit
description: Audit skills against their claims and recent evidence.
tags: [meta, skills, quality]
---


# Skill Audit Protocol

Skills are procedural memory. They get written once, then followed blindly. If the agent that wrote the skill made a mistake, every future session repeats it. This skill prevents that.

## When to Audit

- After any session where a skill's recommendation was wrong or led to a bad outcome
- When the user says "check yourself" or "are you sure about that?"
- When a skill hasn't been audited in 30+ days
- When a skill references external data (APIs, research, prices) that may have changed
- When two skills give contradictory advice

## Audit Checklist

For each skill being used in a session:

### 1. Assumption Check
- What does this skill ASSUME to be true?
- Are those assumptions still true? (e.g., "the timing model has Sharpe 4.2" — is it still 4.2?)
- Has the user's situation changed since the skill was written?

### 2. Contradiction Detection
- Does this skill say two contradictory things? (e.g., "always validate with bootstrap" vs "skip bootstrap when timing model dominates")
- Do multiple skills on the same topic disagree?
- If contradictions exist, which instruction takes precedence?

### 3. Methodology Validation
- Is the skill's methodology appropriate for the CURRENT problem? (e.g., portfolio-level validation is wrong when timing model Sharpe > 5)
- Would an expert in this domain agree with the skill's approach?
- Are there simpler/better approaches the skill doesn't mention?

### 4. Citation Verification
- Does the skill cite research? Are the citations accurate?
- Use MCP (Exa) to verify: search for the paper title, check the finding matches
- Flag citations that are approximate ("87% of backtests fail" — is that actually in the paper?)

### 5. Outcome Tracking
- Did the skill's recommendation work last time it was followed?
- If the user overrode the skill's recommendation, was the user right?
- Are there patterns of the skill being wrong in specific situations?

### 6. Data & Calculation Verification
- Are calculations using the correct library? (e.g., quantstats not manual formulas)
- Is data loading selecting the right column? (e.g., `adjusted_close` not `open`)
- Do results match known benchmarks? (e.g., SPY 10Y Sharpe ≈ 0.88)
- Run verification scripts before presenting metric-heavy analysis
- Cross-check a few stocks against known performance (NVDA should show massive CAGR, not negative)

## Red Flags

Immediately flag a skill for review if:
- The user says "that's wrong" or "why did you do that?"
- The skill recommends the same action regardless of input (one-size-fits-all)
- The skill has been patched 3+ times (may need rewrite, not patch)
- The skill references specific numbers that may be stale (Sharpe ratios, prices, API endpoints)
- The skill contradicts itself (two sections give opposite advice)

## How to Fix

- **Minor fix**: `skill_manage(action='patch')` — correct the specific wrong claim
- **Major fix**: `skill_manage(action='edit')` — rewrite the section with correct methodology
- **Contradiction fix**: Remove the wrong instruction, keep the right one, add a note explaining why
- **Stale data fix**: Remove specific numbers, replace with "compute at runtime" or "check current value"

## Pre-Flight Check (before following ANY skill)

Before executing a skill's methodology, spend 30 seconds asking:

1. **What problem am I actually solving?** (Not "what does the skill say to do" — what is the USER trying to accomplish?)
2. **Is this skill's methodology appropriate for THIS specific situation?** (e.g., portfolio-level validation is wrong when timing model Sharpe > 5)
3. **What would an expert do differently?** (Would a quant skip bootstrap if the timing model already handles risk?)
4. **Am I following the skill because it's right, or because it's written down?** (If the answer is "because it's written down," question it.)

If any answer suggests the skill's methodology is wrong for this situation, say so to the user. Don't follow a wrong methodology just because it's documented.

## The User's Question Test

The most valuable audit is the user asking "why?" If the user asks "why did you do X?" and the answer is "because the skill said so" — that's a red flag. The answer should be "because X is the right approach for this situation because [reason]."

If you can't explain WHY a skill's recommendation is correct (beyond "the skill says so"), you don't understand it well enough to follow it.

**A skill that hasn't been challenged is probably wrong.** If you're following a skill and everything seems to work perfectly, that's suspicious. Push back on the skill's assumptions. Ask: "is this actually the right approach, or am I just following instructions?"

## Case Study: Portfolio Stock Selection (July 2026)

A skill encoded 6 composite weights (Sharpe 15%, Sortino 12%, etc.) and a MaxDD filter on top. The agent followed these for multiple sessions without questioning.

**What happened:**
1. The MaxDD filter double-counted risk penalties (Sharpe/Calmar already penalize drawdowns)
2. The arbitrary weights excluded the best candidates (CSU, CLS, POWL)
3. The skill had contradictory instructions (equal-weight at top, arbitrary weights in code)
4. The user asked "why not just focus on metrics?" — one question unraveled everything

**What should have happened:**
- The agent should have asked "are these weights evidence-based?" before using them
- The agent should have tested multiple weighting schemes before committing
- The agent should have noticed the contradiction between sections
- The agent should have verified the skill's claims against research (IC values)

**Lesson:** When a skill says "use these weights/thresholds/parameters," ask WHY those values. If the answer is "the skill says so," that's not good enough. Verify against research, test alternatives, and pick the simplest approach that works.

## Reference Files

- `Reference: data-verification-checklist` — Step-by-step checklist for verifying data loading, calculation correctness, and benchmark sanity checks. Run before presenting any metric-heavy analysis.

## Reference: data-verification-checklist

# Data & Calculation Verification Checklist

Run this before presenting any metric-heavy analysis.

## 1. Column Selection
```python
# WRONG: falls back to open price
col = df.columns[0]

# CORRECT: explicitly check for adjusted_close
if 'adjusted_close' in df.columns:
    col = 'adjusted_close'
elif 'Close' in df.columns:
    col = 'Close'
else:
    col = df.columns[0]
```

**Bug history (July 2026):** 3 scripts had `adjusted_adjusted_close` (double) which doesn't exist in EODHD CSVs, causing fallback to `open` column. NVDA showed -61% return instead of +25,000%.

## 2. Library vs Manual
- **ALWAYS use quantstats** for Sharpe, Sortino, Calmar, MaxDD, CAGR, Omega, TailRatio, VaR, CVaR
- Manual Sharpe (CAGR/vol) understates by ~5-10% vs quantstats (arith_mean/vol)
- Manual Sortino (std of negative returns) understates by ~10-15% vs quantstats (sqrt(mean(min(r,0)^2)))

```python
import quantstats as qs
sharpe = qs.stats.sharpe(ret, rf=0.0, periods=252)
sortino = qs.stats.sortino(ret, rf=0.0, periods=252)
calmar = qs.stats.calmar(ret)
maxdd = qs.stats.max_drawdown(ret)
cagr = qs.stats.cagr(ret, periods=252)
```

## 3. Benchmark Sanity Checks
| Benchmark | Expected Range | Check |
|-----------|---------------|-------|
| SPY 10Y Sharpe | 0.7-0.9 | `qs.stats.sharpe(spy_ret_10y)` |
| SPY 5Y Sharpe | 0.8-1.2 | `qs.stats.sharpe(spy_ret_5y)` |
| SPY 10Y CAGR | 10-14% | `qs.stats.cagr(spy_ret_10y)` |
| SPY 10Y MaxDD | -20% to -35% | `qs.stats.max_drawdown(spy_ret_10y)` |
| NVDA 5Y CAGR | 50-80% | AI boom, massive growth |
| CPRT 5Y CAGR | -5% to +5% | Underperformed |
| LLY 5Y CAGR | 30-50% | GLP-1 boom |

If any check fails, investigate before presenting.

## 4. Data Quality
```python
# Check for NaN
assert price_series.isna().sum() == 0

# Check for extreme returns (data errors)
returns = price_series.pct_change().dropna()
assert (returns.abs() > 0.5).sum() == 0  # no single-day >50% moves

# Check date range
assert price_series.index[-1] > pd.Timestamp('2025-01-01')  # not stale

# Check for open vs close confusion
# If a stock had a split (e.g., NVDA 10:1 in June 2024), 
# open prices will show a cliff. adjusted_close will show smooth continuity.
```

## 5. EODHD-Specific
- CSV columns: `open, high, low, close, adjusted_close, volume`
- `df.columns[0]` is `open` (WRONG for returns)
- Always use `adjusted_close` for return calculations
- TSX stocks: use `.TO` suffix (e.g., `POW.TO`), no `.US`
- Some Canadian stocks have stale US OTC listings — check last date

## 6. Cross-Check
Pick 2-3 portfolio stocks and verify manually:
```python
# NVDA should show massive positive CAGR
# CPRT should show near-zero or negative CAGR  
# LLY should show strong CAGR (GLP-1 boom)
```
If NVDA shows negative CAGR, you're using `open` instead of `adjusted_close`.
