---
name: open-source-contribution
description: "Evaluate open-source issues for contribution suitability — find easy wins, avoid design-intent traps, tier by certainty."
tags: [GitHub, Open-Source, Contribution, Issue-Triage, First-Issue]
triggers:
  - finding an issue to contribute to
  - evaluating a repo for contribution
  - first open-source PR

---

# Open-Source Contribution: Issue Evaluation

Evaluate GitHub issues in a repo to find suitable contribution opportunities. This skill focuses on the **contributor perspective** — finding issues you can realistically fix, not managing issues as a maintainer.

## When to Use

- User wants to contribute to an open-source project and needs help picking issues
- User asks "which of these issues can I fix?"
- User wants to find good-first-issue opportunities in a repo

## Choosing the Project First (before issue triage)

Repo selection matters more than issue selection. A perfect issue in a dead repo is worthless. See project-selection.md for condensed research and worked repo data; scripts/check_repo_health.py runs the health check.

- Sweet spot: 100–5,000 stars. Under 100 usually abandoned; over 10k, first issues vanish in minutes and review is slow. Activity beats stars every time.
- Health signals: last commit within weeks (not 6+ months), issues answered within days, recently merged PRs closing within ~2 weeks of opening, CONTRIBUTING.md present, CI green, runs locally in under an hour, codebase under ~50k LOC.
- Contribute to tools the user already uses daily (the Kent C. Dodds rule). Domain familiarity collapses ramp-up from "learn the codebase" to "trace one code path through 1-3 files."
- Three-week trial: claim one small issue and open a PR; if maintainers ignore you, drop the project and move on. Sunk cost is the trap. First merged PR is realistic in 2-4 weeks at a few hours/week; the second is much faster.
- GitHub API health check (read-only, no auth): repo info via GET /repos/{owner}/{repo} (stargazers_count, pushed_at, archived, size); merged-PR recency via the SEARCH API (search/issues?q=repo:{owner}/{repo}+type:pr+is:merged&sort=updated&order=desc), NOT the pulls endpoint, which returns stale rows with old merged_at even on active repos; open-PR pressure via search type:pr+is:open. Unauthenticated limit ~60 req/hr, so batch all candidates in one script (403 = rate-limited, back off). A 404 may be a renamed/moved repo (e.g. hynek/attrs → python-attrs/attrs), check before dismissing.

the user preferences (verified Aug 2026):
- Recommend only projects in domains he already works in daily. He rejects libraries/products he'd be clueless in and wants the toolchain companies actually run (Docker, CI/CD, Postgres, cloud, monitoring).
- Give ONE decisive pick backed by checked numbers, not a framework or menu ("you know me then what do you recommend").
- Do not lead with game-dev, endpoint/M365 automation, or the portfolio toolkit unless he raises them himself; he re-opens them on his own terms.

## Workflow

### 1. Find Candidate Issues

Search for issues with contributor-friendly labels:

```
gh issue list --label "good first issue" --state open
gh issue list --label "help wanted" --state open
gh issue list --label "docs" --state open
```

Or via browser: `https://github.com/{owner}/{repo}/issues?q=is:issue+is:open+label:"good+first+issue"`

### 2. Read the Issue + Comments (MANDATORY)

Before recommending ANY issue, you MUST:
- Read the full issue body
- Read ALL comments — especially from maintainers
- Check if someone already claimed it ("I'd like to work on this")
- Look for maintainer guidance on implementation direction

**Never recommend an issue you haven't read the comments on.**

### 3. Assess Fix Clarity

For each candidate, answer these questions:

| Question | Easy | Hard |
|----------|------|------|
| Is the bug clearly defined? | Reproducible, specific | Vague, environment-dependent |
| Is the fix direction obvious? | One correct answer | Multiple valid approaches |
| Does it require design decisions? | No — just fix what's broken | Yes — need to choose behavior |
| Is there maintainer guidance? | Comments confirm approach | Silence or conflicting opinions |
| How many files? | 1-3 | 4+ or cross-cutting |
| Can you test it locally? | Yes, standard setup | Needs specific hardware/OS/config |

### 4. Tier by Certainty

**Tier 1 — Recommend confidently (no ambiguity):**
- Broken links, typos, wrong file extensions
- Missing keyboard handlers where other similar cases exist
- Error messages that are clearly wrong
- Issues with maintainer comments confirming the fix direction
- Labeled "good first issue" with clear description

**Tier 2 — Recommend with caveats:**
- UI bugs with clear reproduction but need to verify intent
- Issues labeled "help wanted" by maintainer
- Missing features where the expected behavior is documented
- Platform-specific bugs with known upstream issues

**Tier 3 — Do NOT recommend (too much ambiguity):**
- Design decisions (should notifications show? should this be a dialog or toast?)
- "Improvement" issues where the maintainer hasn't confirmed the direction
- Issues where multiple people asked to work on it (check for abandoned PRs)
- Platform-specific behavior that might be intentional

### 5. Present Results

Format: tier-ordered list with:
- Issue number and title
- Why it's suitable (specific signal: label, maintainer comment, clear bug)
- Estimated difficulty (files to change, complexity)
- Any caveats

## Pitfalls

### PITFALL: Assuming design intent
If an issue could be "working as designed," do NOT recommend it. Even if it seems like a bug to you, the maintainer may have intended that behavior. Only recommend issues where:
- The maintainer confirmed it's a bug
- The behavior is objectively wrong (wrong file extension, broken link, crash)
- There's a clear pattern in the codebase showing the intended behavior

### PITFALL: Ignoring existing PRs
Check if the issue has linked PRs. If someone already submitted a fix that's pending review, don't recommend the issue. Use `gh issue view N` to see linked PRs.

### PITFALL: Stale "good first issue" labels
Some repos label issues "good first issue" but never update them. An issue from 2023 with 5 "I'd like to work on this" comments and no PR is likely abandoned for a reason — there may be hidden complexity. Mention this as a caveat.

### PITFALL: Recommending issues without reading code
If you can't look at the relevant source code to confirm the fix is straightforward, say so. "Looks easy from the description" is not enough — check the actual code.

## Publishing Your Own Skills or Tools

When the user asks whether to publish their OWN work (skills, scripts, techniques), the test is not "is this non-trivial" — it is whether a stranger would (a) hit a wall they can't solve with a Google search, (b) be able to use it outside your exact stack, and (c) actually search for it. A candidate must pass ALL THREE; most personal skills fail at least one (setup-specific paths, org-shaped queries, crowded topics).

- **Unique**: non-obvious, undocumented elsewhere. If MS docs / community repos already cover it, it fails.
- **Generic**: stack-independent. If it only makes sense with your daemon ports, your org's device count, or your file layout, nobody else can use it.
- **Searched**: an audience that goes looking. Contributing to a thing people already search for beats creating a new repo nobody finds.

Distribution shapes: small hard-won techniques → gist, not repo. Generic knowledge that extends an existing project → upstream PR (e.g. new patterns for blader/humanizer). Repo-shaped skills → only standalone tools with a real audience. Verified Aug 2026: of ~160 skills audited, exactly one technique (the WSL→Windows GUI-exe stdio bridge) passed all three tests, and it's gist-sized.

## Quick Triage Checklist

Before recommending an issue:
- [ ] Read full issue body
- [ ] Read all comments
- [ ] Check for linked PRs
- [ ] Verify no one else is actively working on it
- [ ] Confirm fix direction is unambiguous
- [ ] Check if it requires design decisions
- [ ] Look at labels for maintainer signals
- [ ] Estimate file count and complexity


## Reference: project-selection.md

# OSS Project Selection — Research Notes (Aug 2026)

Condensed from: freecodecamp.org "How to Land Your First Cloud or DevOps Role", showproof.io DevOps portfolio guide, devopsboys.com portfolio + certs-vs-projects articles, ametric.sh picking-a-project path, pullflow.com first-contribution guide, kentcdodds.com "What open source project should I contribute to", techwithsatyam.hashnode.dev 2026 guide, techotlist.com side-projects article, plus live unauthenticated GitHub API checks.

## What actually gets people hired (project level)

- Projects that solve a real problem the author had and that real users adopted: Logdy (terminal log UI, 1.8k stars, 2k runs/day), Jilfred (career-site watcher, landed a SWE job at CVS Health), CV Match (100 installs = interview material), Kinship Careers (40-day build, 55 beta testers), TalentGrep (GitHub-profile analyzer for hiring).
- "AI killed the toy portfolio": in 2026 a generated repo proves nothing. Real users, stranger-filed issues, and months of commits are the unfakeable signals.
- 2-4 strong projects beat 10 half-finished ones. One project done properly (deployed URL, CI/CD, tests, IaC, monitoring, README with architecture diagram + decisions + a "what broke and how I fixed it" writeup, public commit history) beats five.
- Merged OSS PRs carry more weight per hour than solo personal projects: they prove code review, collaboration, and working in unfamiliar code. Prefer smaller active projects where a good PR has real merge odds; big names mean months of ignored PRs.
- First contribution realistically takes a few hours over a couple of days; first merged PR in 2-4 weeks at a few hours/week. You learn the code path, not the codebase.

## Repo selection criteria (consensus across sources)

- Stars: 100-5,000 sweet spot (under 100 = possibly abandoned; over 10k = crowded).
- Recent activity: last commit within ~1 month; issues answered within days; PRs merged regularly.
- Merge cadence: recently merged PRs close within <14 days of opening.
- Green flags: CONTRIBUTING.md, LICENSE, CI green, ~5+ open good-first-issue issues, multiple maintainers.
- Codebase size: <10k LOC great, <50k doable, >100k = a week just to orient.
- Language and domain match: ship in a language you already know, on tools you already use daily (biggest factor).
- Red flags: no commits in 6+ months, dozens of stale open PRs, no contribution guide, can't run locally in 30 minutes, hostile issue threads.

## Worked examples from this session (real API data, Aug 2026)

- game-ci/unity-builder: 1,083 stars, pushed 2026-08-22, merges through May 2026, 17 open PRs. Healthy but repo is ~250 MB (test fixtures).
- game-ci/unity-test-runner: 262 stars, pushed 2026-08-18, merged 2026-08-16, 8 open PRs. Ideal entry size.
- spectreconsole/spectre.console: 11.6k stars, merged 2026-07-27, 17 open PRs. Healthy but competitive.
- encode/httpx: 15.4k stars but last merge Feb 2026, 78 open PRs. Big-name slowing-down trap.
- hynek/structlog: 4.9k stars, merged 2026-08-04, 8 open PRs. Famous welcoming maintainer, ~5k LOC.
- testcontainers/testcontainers-dotnet: 4.4k stars, merged 2026-08-21, 13 open PRs. Best health seen.
- UniToolsTeam/unitools-build (29 stars, dead since 2024), lazysquirrellabs/min_max_range_attribute (26 stars, 0 issues): too small/dead.

## Pitfalls discovered

- GitHub pulls endpoint (?state=closed&sort=updated) returns stale rows (2019 merged_at on active repos). Use the search API for merged dates.
- Unauthenticated GitHub API: ~60 req/hr; HTTP 403 = rate limit. Batch all candidate checks in one script run.
- Repos move orgs: hynek/attrs 404 -> python-attrs/attrs. Don't assume deleted.
- "Good first issue" labels are not promises: check recency, comments, and who claimed it (see SKILL.md triage section).
