---
name: github-actions
description: Use when inspecting or fixing GitHub Actions workflows.
triggers:
  - "github action"
  - "workflow"
  - "check the action"
  - "scheduled job"
  - "gh run"
tags: [github, ci-cd, automation, workflows]
---

# GitHub Actions: Inspection, State Persistence, Secrets

## When to use
Verifying a scheduled workflow actually does its job (green runs are not proof), debugging alert/notification pipelines, persisting state across runs, checking secrets.

## Inspecting runs
- `gh run list --repo O/R --limit N` — status + conclusion per run.
- `gh run view <id> --repo O/R --log` — full log; grep for the script's stdout lines.
- If `--log` returns nothing: `gh api repos/O/R/actions/runs/<id>/jobs` → job id → `gh api repos/O/R/actions/jobs/<jobid>/logs`.
- ALWAYS read the script's actual output in the log. A green run only means the steps exited 0.

## State persistence (the #1 silent killer)
`actions/checkout` gives a FRESH workspace every run. Any state needed across runs (last-signal state, cursors, dedupe markers) MUST be persisted externally — the reliable pattern for small repos is commit-back:

```yaml
jobs:
  x:
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v5
      ...
      - name: Persist state
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add -f .state.json          # -f required when the file is gitignored
          git commit -m "update state [skip ci]" || echo "no state change"
          git push
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Symptom of the missing pattern: script has a "first run — save state, don't alert" branch, workflow runs green daily, but the alert/notification NEVER fires. Confirm with: no state file in the repo, `git log --all -- <statefile>` empty, run logs showing the first-run branch every day. `actions/cache` is a fragile alternative (evictable) — commit-back is the default.

## Secrets
- `gh secret list --repo O/R` — repo Actions secrets (org secrets need `--org`).
- Authoritative check: `gh api repos/O/R/actions/secrets` → `total_count`.
- If the user insists secrets are set but the API shows zero: wrong repo, org-vs-repo level, or environment/Codespaces store (separate).
- A notification step guarded by `if:` that never fires HIDES missing secrets — when it finally fires it fails loudly, which is the desired visibility, not a bug.

## Workflow patch verification loop
After changing a workflow: validate YAML (`python3 -c "import yaml; yaml.safe_load(open(...))"`), commit + push, `gh workflow run <name> --repo O/R` (dispatch), wait, then confirm BOTH the log output AND the repo state (e.g., state file committed). Never declare a fix without the dispatch-run evidence.

## Verifying an alert path that has never fired
A guarded notification step (`if:` on a state-change branch) that has only ever been SKIPPED is unverified — green runs prove nothing. Definitive end-to-end test (private signal repo, Aug 2026):
1. Flip the persisted state file to the opposite value locally (e.g. `{"last_invested": false}` while the live signal is INVESTED), commit, push.
2. `gh workflow run "<name>" --repo O/R`, poll `gh run view <id> --json status,conclusion,jobs`.
3. Expect: the script's change branch prints, the email step shows `completed success` (NOT skipped), and the persist step commits the correct state back — self-restoring. Pull afterward; the persist commit leaves local behind origin.
4. When `gh run view --log` returns nothing, read the log via the jobs API: `gh api repos/O/R/actions/runs/<id>/jobs` → job id → `gh api repos/O/R/actions/jobs/<id>/logs`.

Pitfalls:
- yfinance on GH runners silently returns NaN-filled frames when the runner IP is rate-limited. Symptom: a NoneType crash in a formatter (a NaN guard turned NaN into None). Fix pattern (private signal repo, Aug 2026): validate the series (>=200 rows, last value not NaN), retry 3x with backoff, fall back to the raw Yahoo chart v8 endpoint (query1.finance.yahoo.com/v8/finance/chart/{SYM}?range=1y&interval=1d — keyless, works from runners, distinct path from yfinance's downloader), and FAIL LOUDLY on bad data (clear ERROR line, non-zero exit) rather than print an all-clear — a false OK on a missing-data day silently kills the alert path.
- Local checkout can lag origin (fixes pushed from elsewhere). `git fetch` and inspect `origin/master:` BEFORE concluding the workflow lacks a step — live and local files may differ.
- When sandbox-testing grep-based alert detection, reproduce the workflow's EXACT grep strings. A needle with extra characters (e.g. a delimiter prefixed in) gives a false negative and a fake investigation.
- Repo-level `actions/secrets` showing zero is NOT proof secrets are missing — they may be environment-scoped: `gh api repos/O/R/environments/<name>/secrets`.
- Non-interactive rebase with conflicts: resolve, `git add`, then `GIT_EDITOR=true git rebase --continue`.

## Worked example
A private signal-checking repo audit (state bug + model mismatch).
Model comparison tooling (loose vs frozen timing model, full history) lives in the live environment (requires the price cache).
