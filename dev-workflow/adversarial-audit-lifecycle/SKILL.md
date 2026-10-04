---
name: adversarial-audit-lifecycle
description: Use when a system's claims need independent falsification.
tags: [audit, falsification, critique, triage, corrections, portfolio, methodology]
---


# Adversarial Audit Lifecycle

The full process that exposed the portfolio program's issues (Aug 26 2026): 3 blind
subagent waves (~20 pre-registered falsification tests), IBKR ground-truth
reconciliation, then a triaged fix sequence (tools -> records -> structural rules ->
decisions). Use when a system's claims need independent falsification AND the
findings need to become durable changes. For the subagent dispatch mechanics
(briefs, smoke/full split, 600s timeouts, blind-spot diff) load
`subagent-critique-battery` — this skill covers the end-to-end sequence around it.

## When to use

- A system (portfolio methodology, screener, testing framework, decision machinery)
  has been validated only by its own authors and its claims are quoted as fact.
- Pre-review ritual: run a full critique wave BEFORE each quarterly review so
  verdicts are computed on corrected machinery.
- Any time the user says "test it adversarially" / "critique our X".

## Phase 0 — inventory and seal

1. Read the system's own docs/skills and list its CLAIMS verbatim (they are the
   attack surface; do not paraphrase into your own suspicions).
2. Write YOUR suspected weaknesses to a SEALED list (e.g. /tmp/critique_my_sealed_list.md)
   before dispatch. Never show it to subagents; use it only for the blind-spot diff.
3. Inventory the data layer: caches, scripts, conventions (rf=0, MaxDD sign, CAD
   conversion, quarter-end convention, phantom-ticker pitfalls, tz traps).
4. Dispatch per `subagent-critique-battery` protocol: waves of 3, 2 claims each,
   pre-chewed briefs, smoke/full split, fresh staged directory per wave.

## Phase 1 — execute, don't trust

1. Run every subagent's FULL mode after the wave returns. Subagent scripts carry
   mechanical bugs (~2 per wave): identical numbers across variants = matrix
   alignment bug; unstable p across reruns = selection-order bug; empty windows =
   coverage-guard mismatch.
2. Fix mechanical bugs ONLY, document each fix in the report, and never touch the
   pre-registered bars after results exist.
3. DIRECTION CHECK: note which way each fix moved the numbers. In the 2026 run every
   fix moved results AGAINST the system (positive edges went negative). A fix that
   flips results TOWARD the system deserves extra scrutiny.
4. Save all outputs: per-wave report, raw run files, derived caches (rank windows
   are the expensive artifact — keep them; they make re-runs minutes instead of hours).

## Phase 1.5 — CALIBRATE THE INSTRUMENT (mandatory; skipping this invalidates refutations)

A falsification battery that has never been power-tested cannot distinguish "no effect" from
"effect too small for this bar". Before any refutation is recorded as a verdict, measure the
apparatus itself. This step was MISSING from the Aug 2026 portfolio audit and cost it eleven
waves of overconfident verdicts; the Aug 28 2026 calibration wave overturned them.

1. **Minimum detectable effect (MDE).** Build a synthetic selector with a KNOWN true edge:
   `score = w * (true forward-return rank) + (1-w) * (seeded noise rank)`. Sweep `w` so the
   realized edge spans 0 to well past your bar, use >=5 independent noise seeds per `w`, and
   run each through the REAL bars. Report the pass RATE per `w`. The smallest edge with >=80%
   pass rate is the MDE. Anything below it was never testable, and "refuted" there means only
   "not detectable".
2. **Bar coherence.** If the design has both a magnitude bar (e.g. median excess > +1%/q) and a
   consistency bar (e.g. >=17/24 wins), check they are compatible: compute
   `P(>=k wins | Binom(n, p))` where `p` is the per-period win probability a mechanism with
   exactly the magnitude-bar edge produces (derive `p` from the measured cross-sample SD).
   Mutually incoherent bars demand modest magnitude AND near-impossible consistency, so they
   refute real effects by construction. Measured example: SD 5.11%/q gave a real +1%/q edge only
   a 13.7% chance of clearing 17/24, while the magnitude bar called +1%/q meaningful.
3. **False-positive rate.** Run pure-noise selectors (>=40 seeds) through the same bars. You
   need BOTH numbers: a bar can be conservative on size and blind on power simultaneously, and
   that trade-off must be a stated choice, not an accident.
4. **Known-good benchmark.** Push something that unambiguously works (the market index itself,
   a hindsight-contaminated basket) through the bars. If the index FAILS your bar, the bar is
   not measuring "is this good" — it is measuring "beats a same-universe dartboard". Every
   verdict must then be scoped accordingly. Measured example: SPY scored 11/24 vs random
   baskets drawn from a survivor-heavy pool that compounded 24.5%/yr vs SPY's 18%.
5. **Derive bars from the power curve, not from habit** — and derive them BEFORE seeing results,
   recording the target effect size and power level in the pre-registration. Always report the
   old bar's outcome alongside the new one, or bar-derivation becomes goalpost-moving.

## Phase 1.6 — SAMPLE/IMPLEMENTATION CONFOUND CHECKS

Before attributing a result change to the variable you meant to test, prove nothing else moved:
- **Same seed + different pool size = DIFFERENT SAMPLE.** Seeded draws are not stable across
  population changes. Measured example: a 3.5% filter change (47 of 1,350 names) produced samples
  overlapping on only 22.4% of names, and the resulting "collapse" of 9 cells was the resample,
  not the filter (resample delta positive in 9 of 9 cells, sign-test p=0.004). ALWAYS run a
  PAIRED arm where the same names are used on both sides and only the tested variable changes.
- **Mirror-gate every reimplementation.** If a "confirmation" script recomputes metrics, assert
  spearman == 1.0 against the original implementation per cell before comparing verdicts.
  Measured example: three metrics were near-identical (0.997-0.998) but not identical, one had
  spearman 0.115 (a different signal entirely), and one was structurally uncomputable under the
  new script's minimum-observation floor — reported as a "collapse" rather than as a bug.
- **Benchmark symmetry.** Verify the comparison set can actually contain the thing being tested
  (e.g. random baskets drawn US-only while the tested basket holds TSX names flatters the test).

## Phase 2 — the change list: triage into four buckets

The core governance move. Every finding lands in exactly one bucket:

- **BUCKET A — forced tool fixes**: the software does not implement its own
  documented rules (MIN_DELTA never enforced, quarter-end computed as QEND-5d,
  DSR hardcoded N=31, walk-forward picked set-iteration order, cache stores symbols
  so name_sweep can't run, ticker-reuse history mixed in, holdings fall out of
  builds). No user decision needed — the code is wrong.
- **BUCKET B — forced record corrections**: documented claims that fail
  re-derivation (e.g. a persistence claim built on a date bug, an
  unreproducible benchmark anchor, a headline result voided by a selection-
  order bug, a concentration claim that is arithmetically impossible for the
  universe, validation ratios that cannot discriminate accepted from
  rejected candidates, a selector re-labeled governance-not-forecast). The
  user's rule: corrections get RECORDED, not defended.
- **BUCKET C — structural rules**: changes that bind future work (null control in
  every validation, independent falsifier at every review, survivorship quantified
  in every report, headline numbers re-derived in-session, search size vs pair
  count in multiple-testing math). Write these into the methodology skill so they
  outlive the session.
- **BUCKET D — decisions**: choices with real trade-offs where the data does
  not force an answer (the selection layer's role after its forecast power is
  falsified, a redundant signal leg, rebalance cadence, live lane battery
  re-run, automation economics at executable gating). These go to the user;
  never decide them silently. Sequence: A -> B -> C -> D, and optional
  re-checks after D.

## Phase 3 — apply forced fixes (A) and verify each

Fix, then RUN the fixed artifact and show the output changed as expected.
Generic verification patterns (do NOT copy specific numbers from prior runs —
re-derive them fresh each audit; prior numbers live only in the on-disk
reports, never in this skill):
- audit script: the persistence candidate set should shrink after the
  quarter-end bug fix; flagged holdings and lane count should be recomputed.
- DSR/multiple-testing: the verdict often flips when evaluated at the true
  search size instead of the recorded pair count.
- cache build: hard-fail on missing universe members; clip ticker-reuse
  history so mixed-company series are impossible.
- walk-forward: assert the selected top-N equals the N best scores in the
  member set (never set-iteration order).

## Phase 4 — correct the records (B) in the skills

- Add one CRITIQUE-CORRECTIONS block near the top of the owning skill listing every
  voided claim with the corrected value and the date.
- Also patch the SPECIFIC stale lines in place (the false "5Q persistence" bullet,
  the wrong binomial table) so nobody quotes the old number again.
- Add the ground-truth caveat: any reconstruction-based numbers (swap record, EV
  battery) get "describes the model, not the account" if a reconciliation exists.

## Phase 5 — structural rules (C) into the methodology skill

Write the mandatory rules as numbered items in the skill that governs future work.
They must be phrased as requirements ("MUST include a noise arm"), not suggestions.

## Phase 6 — ground-truth reconciliation (do this if the system trades)

Parse the account statements (HTML MTM summaries work with pandas.read_html;
CSV exports sometimes drop trade dates — use HTML for dates when that
happens), then compute, fresh each time, against the model's assumptions:
- commissions actual vs model estimate (often 1.5-2x the estimate)
- fill-vs-close slippage (next-close assumption is usually fair on the
  median but fat-tailed on individual orders — report both)
- execution dates vs assumed wave dates (often entirely different)
- window P/L decomposition: realized trading + commissions + dividends
  (dividends are real return the simulation may ignore)
- end-state holdings vs the model's book (watch for alternate listings,
  e.g. CDRs vs US shares)
Record the caveat (Bucket B): reconstruction-based numbers describe the
model, not the account. Keep the report on disk.

## Pitfalls

- **Triage refutations by FAILURE MODE before trusting any of them.** Low power cannot
  manufacture a wrong-direction result, so the two classes are not equally fragile:
  - Failed on DIRECTION or MAGNITUDE (mechanism lost consistently, or median excess ~0 /
    negative) -> the refutation SURVIVES a power correction. An underpowered test cannot make a
    real edge look reliably negative.
  - Failed on CONSISTENCY ONLY while clearing the magnitude bar (e.g. 15-16/24 wins with
    +3-6%/q median excess) -> NOT REFUTED, only NOT PROVEN. That is the ordinary outcome for a
    real edge of that size; re-test with a powered bar and more observations.
  Record verdicts with the failure mode attached, or a future session will re-assert
  "everything was refuted" when half the pile was merely undetectable.
- **Buy observations before weakening bars.** When power is the binding constraint, extending the
  frame (more periods) is honest; loosening the bar without a power derivation is not.
- NEVER store prior-audit findings inside this skill or any skill. Skills
  are loaded by future sessions; a findings file here would contaminate the
  next audit's briefs with the answers. The canonical record is the audit
  report directories on disk (e.g. /home/<user>/portfolio_audit/critique{,2,3}/).
  Re-derive every number fresh each run; never copy numbers from prior runs.
- Never put prior-wave findings in a new wave's briefs; stage clean
  directories and point briefs only at them.
- Never change a bar after results exist; the bars are the contract.
- Skills/records are NOT updated during the critique run — only after
  sign-off on the change list (the user's "no changes yet" stance).
- Meta-lessons (the why): same-brain testing misses everything, so the
  targets come from subagents; rulers tuned until the subject passes measure
  nothing (standardization choices can flip a verdict entirely); cited-
  never-derived numbers fail re-derivation (verify every headline in-
  session); no null control means no false-positive knowledge (add the noise
  arm).
- Preserve the sealed list + pre-registrations: they are the proof the
  verdicts were not post-hoc.
