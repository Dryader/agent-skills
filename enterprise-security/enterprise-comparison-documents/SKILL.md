---
name: enterprise-comparison-documents
description: |
  Create multi-format enterprise technology comparison and recommendation documents
  (markdown + PowerPoint). Covers research methodology, document structure, depth
  calibration, and iteration workflow. For any task involving "compare X vs Y vs Z",
  "recommend a solution for", "write a strategy doc for", or "create a presentation
  about" enterprise technology decisions.
triggers:
  - compare technology options
  - recommend a solution
  - strategy document
  - implementation guide
  - enterprise comparison
  - create a presentation about
tags: [security, enterprise, documentation, comparisons]
---

# Enterprise Comparison & Recommendation Documents

## References

- enterprise-app-control-research.md — comprehensive research bank for enterprise application control (WDAC, AppLocker, CyberArk, Intune EPM, Santa, licensing, gotchas)
- portable-app-control-deep-dive.md — deep dive on controlling portable/non-admin-installed applications, including what actually breaks if you blanket deny user-writable paths, the CyberArk User-Based Application containment framework, and correct AppLocker rule structure
- enterprise-app-control-vendor-comparison.md — vendor comparison for portable app governance (CyberArk, Ivanti, ThreatLocker, BeyondTrust, Carbon Black), including how each vendor handles user-context apps and the "trusted ownership" pattern
- pptx-layout-pitfalls.md — PPTX layout pitfalls: fit:'shrink' doesn't work in PowerPoint, LAYOUT_16x9 vs LAYOUT_WIDE dimensions, boundary validation, vertical centering, visual QA workflow
- strategy-document-notes.md — strategy-document writing notes
- application-control-domain.md — application-control domain knowledge (quick-lookup summary of the enterprise-application-control skill)
- osfi-b13-requirements.md — OSFI B-13 requirements mapping

## When to Use

Any time the user asks you to:
- Compare enterprise technology options (tools, platforms, approaches)
- Write a recommendation or strategy document
- Create both a presentation (.pptx) and document (.md) on the same topic
- Research and document implementation approaches for enterprise IT/security

## Depth Calibration (Critical)

Users iteratively refine the depth they want. Watch for these signals:

| Signal | What It Means | Fix |
|---|---|---|
| "this is very high level" | Too shallow, need more substance | Add mechanism explanations, tradeoffs, operational details |
| "too executive" | Skimming the surface, need depth | Explain HOW things work, not just WHAT they are |
| "too technical / nitty gritty" | Too much config detail | Remove commands, OMA-URI paths, Event IDs. Keep mechanisms. |
| "more depth but not nitty gritty" | Sweet spot: explain mechanisms, not configs | Describe the operational model, day-to-day workflow, what users see |
| User edits the output file | Infer preferences from what they kept/cut/changed | Diff their version against yours, update accordingly |

**The sweet spot for most enterprise audiences:** Executive framing with technical substance. Explain mechanisms and tradeoffs, not commands and configs. Each component gets:
- **How it works** — the mechanism, not the config
- **Why it matters** — the security/operational benefit (see "WHY This Matters" pattern below)
- **Day-to-day operations** — what users see, what admins do, what the workflow looks like
- **What it doesn't do** — honest limitations

### "WHY This Matters" Pattern (Critical)

Every feature, tool, or capability described in the document MUST include a "WHY" explanation. Don't just list what something does — explain why it matters to the audience. This transforms a feature list into a persuasive argument.

**Pattern:** `[Feature] — WHY: [benefit to the audience]`

**Examples:**
- ❌ "Intelligent Security Graph (ISG) reputation"
- ✅ "Intelligent Security Graph (ISG) — Microsoft's cloud reputation service. WHY: auto-trusts known-good software (Chrome, Zoom, etc.) so we don't manually allowlist every app. Saves hundreds of hours of policy maintenance."

- ❌ "Publisher rules (certificate-based)"
- ✅ "Publisher rules (certificate-based) — allow all versions of software from a trusted publisher. WHY: when Adobe ships a new Acrobat, the publisher rule still covers it. Hash rules would break on every update."

- ❌ "Self-Service + Just-In-Time (JIT) privilege elevation"
- ✅ "Self-Service + Just-In-Time (JIT) privilege elevation — WHY: users request temporary admin when needed, approved by manager or auto-approved by risk engine. No standing admin rights."

- ❌ "Approval workflows: self-service, designated approvers, social voting"
- ✅ "Approval workflows: self-service, designated approvers, social voting — WHY: when Lockdown blocks something a user needs, they get it approved in minutes, not days. No helpdesk bottleneck."

**Where to apply this pattern:**
- Tool comparison tables (add WHY column or inline explanation)
- Feature bullet lists (every bullet gets a WHY suffix)
- Implementation steps (each step explains why it matters)
- Summary tables (the "Why" column should be substantive, not just a feature list)

**The WHY should answer one of these:**
1. What work does this save us? (reduces manual effort, automates something)
2. What attack does this stop? (blocks a specific technique)
3. What breakage does this prevent? (avoids user friction, helpdesk tickets)
4. What compliance requirement does this meet? (OSFI, Essential Eight, etc.)
5. What operational model does this enable? (self-service, staged rollout, etc.)

**Depth spectrum:**
```
Executive ←――――――――――――――――――――――――――→ Technical
"WDAC provides    "WDAC runs at kernel    "Deploy via OMA-URI:
kernel-level      level via ci.dll,       ./Vendor/MSFT/
enforcement"      cannot be disabled by   ApplicationControl/
                  admin, uses HVCI to     Policies/{GUID}/Policy,
                  protect policy from     rename .cip to .bin,
                  kernel exploits"        350KB limit"
```
Most users want the MIDDLE column.

## Document Structure

The structure that works for enterprise comparison documents:

### Markdown Document
```
1. Recommended Approach (table mapping needs → tools → rationale)
2. How Each Component Works (dedicated section per tool)
   - Mechanism explanation
   - Day-to-day operations
   - What it doesn't do
3. Implementation Roadmap (phased, with gates)
4. 3rd Party Alternatives (with "when to switch" guidance)
5. Risk & Mitigation
6. Summary (Q&A format)
```

**Key structural decisions:**
- Lead with the recommendation, not the problem statement (audience already knows the problem)
- Don't include a "what we already have" explainer unless the audience doesn't know the licensing
- Don't include A/B/C option comparison unless the audience needs to make a decision (if you're recommending, just recommend)
- Each tool/component gets its own section with enough room to breathe

### PowerPoint Presentation
- Follow the same structure as the markdown
- Each major component gets its own slide (don't cram multiple tools onto one slide)
- Use two-column layouts: left = how it works, right = operations/gotchas
- Include a "key gotcha" or "key principle" callout box
- Summary slide in Q&A format works well

## Research Methodology

When researching enterprise technology:
1. Use Exa MCP (`web_search_exa`, `web_fetch_exa`) for authoritative sources
2. Prioritize: official docs (Microsoft Learn, vendor docs) > community technical blogs > analyst reports
3. Verify licensing claims — vendors bundle features into different tiers, and tiers change (e.g., Intune Suite features moving into M365 E5 in July 2026)
4. Check for recent changes — enterprise licensing and features shift quarterly
5. Cross-reference claims across multiple sources before stating them
6. **Verify technical claims before finalizing.** Common errors: rule evaluation order (Deny → Allow → MI → ISG → Implicit Deny, NOT "Publisher → MI → Hash → Deny"), pricing (vendors don't publish — use Vendr/SpendHound/Forrester TEI benchmarks), feature support by OS version (changes frequently), gotchas that only surface in deployment
7. **Verify pricing using benchmarks.** ThreatLocker: $2-5/endpoint/month (Forrester TEI: $40.40/endpoint/year for 10K). BeyondTrust: $10-40/user/month (Vendr median $17,795/year). CrowdStrike: $60-240/endpoint/year. Don't guess — search for actual benchmarks.

### Verification Batching (Important)

When the user asks to "verify everything" or "make sure it's accurate":
1. **Batch 5-10 searches per call** — don't do one search per turn
2. **Don't stop after each batch** — the user explicitly complained about stopping every 5 lookups. Continue autonomously until you've covered all claims (aim for 20-30 total lookups)
3. **Group related claims** — search for "WDAC known issues 2025 2026" instead of separate searches for each gotcha
4. **Cross-reference** — verify the same claim from multiple sources (official docs + community blog + CVE database)
5. **Report corrections** — when a claim is wrong, show before/after with the source
6. **Summarize at the end** — list all verified claims and all corrections made

## Multi-Format Delivery

When creating both .pptx and .md:
1. Research first (MCP calls)
2. Write the markdown document (source of truth for content)
3. Create the PowerPoint from the markdown (subset of content, visual layout)
4. Both files go to user's Downloads folder (`/mnt/c/Users/<username>/Downloads/`)
5. When user edits one format, infer preferences and update the other

## Debate Pattern (When User Asks "Which Is Better?")

When the user asks you to evaluate two competing approaches (e.g., "CyberArk EPM vs WDAC for everything"), use the debate pattern:

1. **Dispatch two subagents in parallel** — one argues for each side
2. **Each subagent uses MCP** to research and build the strongest possible case
3. **Dispatch a THIRD subagent as judge** — don't judge yourself (user explicitly corrected this: "instead dispatch a subagent to judge the results rather than you")
4. **Present the judge's verdict** with specific evidence from both sides

**Prompt design principles:**
- **Don't guide what advocates should look for.** User explicitly said "dont guide it to what its supposed to look for." Let them find their own evidence via MCP.
- **Tell them to specifically attack the OTHER side**, not just promote their own.
- **Be explicit about the scope** (governance vs security, cost vs features, etc.)
- **Don't mention specific tools/CVEs/approaches in the prompt** — this biases the research.

**Example prompts (unbiased):**
```
Subagent 1: "You are arguing that [Option A] is BETTER than [Option B] for [specific use case]. Your job is to specifically attack [Option B]'s weaknesses and prove why [Option A] is the superior choice OVER [Option B]. Research using MCP web search. Find whatever evidence you can — don't look for specific things, just find what's out there that supports your position. Build a structured argument with citations."

Subagent 2: [Same prompt with A and B swapped]

Judge: "You are an impartial judge evaluating a debate between two advocates. Read both arguments, evaluate each on its merits, determine a winner for the specific question of [scope], provide a detailed evidence-based judgment, and be honest."
```

**Why a separate judge subagent:**
- The parent agent has context from the conversation that biases judgment
- A fresh subagent evaluates only the evidence presented
- User explicitly requested this pattern

**Run multiple rounds for complex decisions:**
- Round 1: General arguments (each promotes their own side)
- Round 2: Attack arguments (each attacks the other side specifically)
- Round 3: Judge evaluates both rounds

**Judging criteria:**
- Verified claims (CVEs, official docs, community evidence)
- Specific capabilities (not marketing copy)
- Operational reality (what works in practice)
- Cost/licensing (what's already paid for)
- Compliance requirements (what auditors expect)

**The verdict should acknowledge:**
- Both sides have valid points
- The right answer depends on the specific use case
- The compromise that captures the best of both

## Iteration Workflow

When the user edits the output files:
1. Extract the edited file (e.g., `python -m markitdown file.pptx`)
2. Compare against what you originally created
3. Infer what they kept, cut, reworded, or reordered
4. Update both documents to match their preferences
5. Don't overwrite their edited file — only update the version in your working directory, then copy to Downloads

## PPTX Layout Pitfalls (Critical)

### fit:'shrink' Doesn't Work in PowerPoint
PptxGenJS's `fit: 'shrink'` option sets "Shrink text on overflow" in PowerPoint, but PowerPoint doesn't apply it until you edit the text. LibreOffice applies it correctly.

**Fix:** After generating PPTX with PptxGenJS, re-save via LibreOffice headless:
```bash
libreoffice --headless --convert-to pptx /tmp/input.pptx --outdir /tmp/output/
```
This triggers the shrink behavior. Then copy the LibreOffice-processed file to the user.

### LAYOUT_16x9 vs LAYOUT_WIDE
- `LAYOUT_16x9` = 10" × 5.625" (standard PowerPoint)
- `LAYOUT_WIDE` = 13.33" × 7.5" (widescreen)
- If element coordinates are designed for 13.33×7.5 but you use LAYOUT_16x9, elements will go off the slide. Always match layout to coordinates.

### Boundary Validation
Add a post-generation validation that checks all elements fit within slide boundaries:
- y + h <= slide height (7.5 for LAYOUT_WIDE)
- x + w <= slide width (13.33 for LAYOUT_WIDE)
- Log warnings for violations, auto-clamp if needed

### Vertical Centering
When content doesn't fill the slide, don't just add `_yShift` to all elements — this causes inconsistent positioning. Instead:
1. Calculate the actual content height (last element Y+H - first element Y)
2. Calculate the shift: (slide_height - content_height) / 2
3. Apply the shift to all body elements, keeping footer/accent bar fixed

### User Corrections on Layout
- "stuff is cutoff" → check y+h <= slide height for all elements
- "not using the space effectively" → content is too small, increase font sizes or split across more slides
- "presentation goes off the slide" → elements positioned beyond slide boundaries, not just text overflow
- "some of them arent using the space effectively now though just being small" → validation clamping made elements too small, better to split content across multiple slides

## Presentation Visual QA

After generating a PPTX, always check for visual issues (overlapping text, cutoff content, text too small):

1. **Render PPTX to PDF:** `libreoffice --headless --convert-to pdf file.pptx --outdir /tmp/slides/`
2. **Convert PDF pages to PNG:**
   ```python
   import fitz
   doc = fitz.open('/tmp/slides/file.pdf')
   for i, page in enumerate(doc):
       page.get_pixmap(dpi=150).save(f'/tmp/slides/slide_{i+1:02d}.png')
   ```
3. **Check each slide with vision_analyze** — ask "Is all content fully visible? Any cutoff, overlap, or text issues?"
4. **Fix issues** by adjusting container sizes, bullet list heights, or card positions in the pptxgenjs source
5. **Re-render and re-check** until all slides are clean

**Common issues and fixes:**
- Text cutoff at bottom of card → increase card height or bullet list height
- Overlap between cards/footer → increase spacing between elements
- Text too small → reduce bullet count or increase slide count (split content across more slides)

**User explicitly asked for this workflow** — "is there some tool that lets you see overlapping text etc on a presentation so you can tune the visuals"

## Pitfalls

- **Stay focused on the specific topic.** If the user asks about application control (execution blocking), don't drift into privilege management (JIT elevation), password vaulting, credential theft prevention, or compliance mapping. These are related but separate domains. Include them only if the user explicitly asks. When in doubt, ask "this touches on X — should I include that or keep focused on Y?"
- **Don't start with problem statements** unless the audience doesn't know the problem. Most enterprise audiences already know what application control is — they want the plan.
- **Don't include A/B/C option comparisons** if you're making a recommendation. Just recommend. Options slides are for when the audience needs to decide.
- **Don't mention evaluating alternatives that don't add value.** If a 3rd party tool offers the same capabilities as the existing stack, just remove it entirely. Don't say "we evaluated X and decided against it." The user finds this pointless. Only include 3rd party options if they offer something genuinely different.
- **Don't cram multiple components onto one slide.** Each tool/approach deserves its own space to explain the mechanism and operational model.
- **Don't use commands/configs in presentations.** Save those for the markdown companion document. Presentations explain mechanisms and tradeoffs.
- **Server and macOS coverage must be substantive.** Not just "what changes" — explain how the tools work on each platform, what's different, what the gotchas are. Include feature support matrices for servers (e.g., WDAC features by Server OS version).
- **Don't forget "what it doesn't do."** Honest limitations build credibility. Every tool has gaps.
- **Don't recommend blanket deny rules for user-writable paths** (AppData, Downloads, Temp) without explaining what breaks. Chrome, Teams, VS Code, Discord, OneDrive all install to AppData. The correct approach is publisher rules (allow signed apps from approved vendors) + deny unsigned/unknown code. Publisher rules evaluate BEFORE path rules in AppLocker, so signed apps from approved publishers are allowed even in user-writable locations.
- **Always verify domain-specific claims using MCP before finalizing.** Search for official docs, community blogs, and recent changes. Cross-reference claims across multiple sources. Pay special attention to: pricing (vendors don't publish, use Vendr/SpendHound benchmarks), rule evaluation order (often misunderstood), feature support by OS version (changes frequently), and gotchas that only surface in deployment.
- **Iteration pattern:** Users may oscillate multiple times between "too high-level" and "too nitty-gritty." Don't get frustrated — this is normal calibration. The sweet spot is mechanisms + gotchas + operational model, skip the config. Ask "what would you add?" to let the user guide depth.
- **Ask "what else would you add?" periodically.** This lets the user guide the depth and scope. Don't just keep adding content — let them decide when it's enough.
- **Focus laser-tight on the specific topic.** If the user asks about portable/user-context application execution control, don't add: JIT elevation, password vaulting, credential theft prevention, compliance mapping, stakeholder RACI, risk assessment. These are related but separate domains. The user will tell you if they want them. When in doubt, the answer is NO — keep focused.
- **"What else would you add?" is not an invitation to add everything.** When the user asks this, suggest options and let them pick. Don't just dump all suggestions into the document.
- **Continue verifying autonomously.** When the user says "verify everything" or "keep checking," batch 20-30 lookups without stopping. Don't ask "want me to continue?" after every 5 searches — just keep going until all claims are verified.
- **PPTX generation cleanup.** After generating PPTX, always clean up: `rm -rf node_modules package.json package-lock.json create_pptx.js`. But watch for approval prompts on recursive delete — if blocked, just note the files for user to clean up.
- **mkRow helper in pptxgenjs — cols must be flat strings, NOT nested arrays.** When building table rows with a helper function, the cols parameter must be `["col1", "col2", "col3"]`, not `["col1", ["col2"], ["col3"]]`. Nested arrays cause SyntaxError or corrupted output. Easy to accidentally do when copy-pasting between rows.
- **Distinguish governance vs security framing.** When the user asks about "governing" applications, they mean: discovery, graduated controls, identity-aware targeting, operational manageability, exception workflows. This is DIFFERENT from "security" which means: kernel enforcement, tamper resistance, CVE-class boundaries. Don't conflate the two. If the user says "this is for governance, not threats," adjust your framing accordingly. Governance = what users can run and what apps can access. Security = defending against sophisticated attackers.
- **Don't bias research prompts.** When dispatching subagents for research, don't tell them what to look for. Let them find their own evidence. User explicitly corrected this: "dont guide it to what its supposed to look for." Biased prompts produce biased results.
- **Diplomatic framing when recommendations change.** When research reveals the initial recommendation was wrong, NEVER frame it as "we were wrong" or "X can't do Y." The user explicitly corrected this: "this makes me look terrible saying it cant handle portable apps." Instead, frame it as: "X was designed for [different purpose], not [current purpose]. Our existing Y has a purpose-built framework for this exact problem. This is the right tool for the right job." The narrative should be evolution, not correction. The audience doesn't need to know the initial recommendation was wrong — they need to know why the final recommendation is right.
- **"What do other companies do?" research pattern.** When the user asks how other companies handle a problem, search for: (1) vendor case studies and customer stories, (2) deployment surveys and adoption statistics, (3) community forums and practitioner blogs, (4) analyst reports. Don't just compare features — find evidence of what enterprises actually deploy. The stat "less than 15% of enterprises have WDAC enforced" was more persuasive than any feature comparison.
- **"Is there a combo worth implementing?" pattern.** When evaluating whether to use multiple tools together, focus on what each tool does BEST and minimize overlap. The answer is usually: use Tool A for what Tool B can't do, and vice versa. Don't try to make one tool do everything. The recommendation should be: "Use [existing tool] for everything it can do. Use [new tool] only for what [existing tool] can't do."
- **Verify domain-specific claims about "what enterprises actually do."** When making claims about industry adoption ("most enterprises use EPM tools for governance"), verify with case studies, deployment surveys, and vendor customer stories. Don't just assert — find evidence. The user was persuaded by "Northern Trust deployed CyberArk EPM across 50,000 endpoints in 16 days" more than by feature lists.

## Related content
The Debate Pattern in this skill lives canonically in dev-workflow/subagent-debate.


## Reference: application-control-domain.md

# Application Control Domain Knowledge

## WDAC (App Control for Business) vs AppLocker

### Enforcement Architecture
- **WDAC:** Kernel-level (ci.dll). Cannot be disabled by local admin. With HVCI, even kernel exploits can't modify active policy. MSRC servicing criteria = security boundary.
- **AppLocker:** User-mode (AppIDSvc service). `Stop-Service AppIDSvc` bypasses it. Feature-complete (no new dev). NOT a security boundary per MSRC.

### When to Use AppLocker Despite WDAC
- Per-user rules on shared devices (WDAC is per-device only)
- Managed installer plumbing (WDAC Option 13 requires AppLocker ManagedInstaller rule collection)
- Legacy OS support (pre-1903)

### Multi-Policy Format
- Win10 1903+, Server 2022+ only
- Up to 32 active policies per device
- Supplemental policies extend base without modifying it
- Deploy via ApplicationControl CSP (rebootless) — NOT AppLocker CSP (forces reboot)
- GPO only supports single-policy format

### Managed Installer
- AppLocker policy defines the managed installer process (IME or CCMExec)
- When MI installs an app, Windows tags files with NTFS Extended Attribute `$KERNEL.SMARTLOCKER.ORIGINCLAIM`
- WDAC Option 13 checks for this EA before blocking
- Trust propagates down process tree
- Only tags files installed AFTER policy active (backlog problem)
- Self-updating apps break MI trust (updates outside channel aren't tagged)
- AppLocker CSP doesn't support ManagedInstaller rule collection — needs PowerShell script
- Intune uses AuditOnly for ManagedInstaller RuleCollection (generates 8003 warnings)
- ConfigMgr uses Enabled mode (generates 8004 errors)

### Rule Evaluation Order (Verified)
1. Explicit DENY (always wins, cannot be overridden)
2. Explicit ALLOW (base policy → supplemental)
3. Managed Installer EA check
4. ISG EA check (cached) → ISG cloud query
5. Implicit DENY (default block)

### Path Rules
- WDAC enforces admin-write-only for path rules — won't let you create rules for user-writable dirs
- AppLocker path rules CAN target user-writable locations, but this is a security hole
- WDAC FilePath rules: user-mode only, symlink protection (Option 18), admin-write requirement

### Key Gotchas
1. Signed base policies require reboot on Win11 <24H2 with HVCI (deploy via script)
2. 350KB OMA-URI limit — use signer rules + managed installer
3. PowerShell CLM breaks many scripts — test before enabling
4. Deny rules in supplemental policies are silently ignored
5. `Add-SignerRule` resets HvciOptions to 0 — always run `Set-HVCIOptions` after
6. Supplemental signer rules go on BASE policy, not supplemental
7. Empty deployed policy = nothing runs (including Windows)
8. MSI files always detected as user-writable on Win10 and Server 2022 and earlier
9. Option 19 (Dynamic Code Security) always enforced in audit mode
10. ISG trust laundering: ISG-trusted apps can pass trust to arbitrary executables they write
11. AppLocker doesn't enforce on services by default — needs RuleCollectionExtensions XML
12. AppLocker blind spot: ignores NT AUTHORITY\SERVICE processes

### WDAC Bypasses (Verified in the Wild)
1. **IME -PowerShell command injection:** Standard user can write files with MI trust, bypassing WDAC + CLM. MITIGATION: signed policies + HVCI.
2. **imgmgr.exe deserialization (CVE-2026-25166):** Windows ADK binary bypasses WDAC via insecure deserialization. Not on Microsoft's block list yet. MITIGATION: add to custom deny policy.
3. **EDR disabling via crafted policy:** Admin can place crafted WDAC policy in `C:\Windows\System32\CodeIntegrity` to disable EDR. MITIGATION: signed policies + HVCI protect against this.
4. **CVE-2025-33069:** Improper cryptographic signature verification. CVSS 5.1. Fixed June 2025 Patch Tuesday.

### ISG (Intelligent Security Graph)
- Microsoft's cloud reputation service
- Auto-trusts known-good software (Chrome, Zoom, etc.)
- Reduces manual allowlisting work significantly
- Does NOT meet Essential Eight "organization-approved set" requirement
- Not recommended for air-gapped devices (requires internet)
- ISG + Managed Installer = over-authorization (dramatically increases trusted surface)

### WDAC CA Expiration (July 2025)
- Microsoft's 15-year issuing CAs begin expiring July 2025
- New handling logic auto-infers trust for new 2023/2024 CAs
- No policy update needed for most deployments
- Can opt out with "Disabled:Default Windows Certificate Remapping"

### Server-Specific Considerations
- Server 2016: Single-policy format only, no managed installer, no ISG
- Server 2019: Managed installer + ISG, still single policy
- Server 2022+: Full multi-policy support
- HVCI not default on servers — need to enable explicitly
- Boot Audit on Failure (ALWAYS enable) — auto-switches to audit mode if policy blocks critical driver
- Group Policy limited to single-policy format (Server 2016/2019)

## CyberArk EPM

### User-Based Application Containment (3-layer)
1. Restrict ALL user-based apps from sensitive OS components (PowerShell, cmd, WMI)
2. Allowlist sanctioned apps by location + publisher + original filename + checksum
3. Default-deny for unknown apps (discovery mode first, then enforce)

### Mutual Exclusions (Critical)
Exclude from CyberArk EPM:
- `C:\ProgramData\Microsoft\Windows Defender\Platform\*`
- `C:\Program Files (x86)\Microsoft Intune Management Extension\*`
- `C:\Windows\System32\CodeIntegrity\*`

Exclude CyberArk from other tools:
- `C:\Program Files\CyberArk\Endpoint Privilege Manager\Agent\*`
- `C:\Windows\System32\drivers\vfdrv.sys`, `vfnet.sys`, `vfpd.sys`, `CybKernelTracker.sys`

macOS (Agent 11.5+): `/Applications/CyberArk EPM.app`, `/Library/Application Support/CyberArk`

### CyberArk EPM + Intune Integration
- "Exclude service accounts from access restrictions" setting must be DISABLED for Intune "Install as system" to work with EPM
- Without this, system-level processes bypass EPM policy evaluation

### CyberArk EPM macOS (v26.5)
- macOS Script Validation via Team ID and Signing ID
- Supported interpreters: /bin/bash, /bin/csh, /bin/ksh, /bin/sh, /bin/tcsh, /bin/zsh
- Homebrew installation fails with EPM due to admin rights assumptions — needs customized script
- Only elevate macOS applications if notarized by Apple or protected by SIP
- Set Monitor SIP files in Agent Configuration to On

## Intune EPM

### Elevation Types
- **Automatic:** Silent elevation, no user prompt. For trusted low-risk apps.
- **User-confirmed:** Right-click → Run with elevated access. Optional: business justification, Windows auth.
- **Support-approved:** User submits request → admin approves in Intune console (24hr window).
- **Deny:** Blocked entirely.
- **Elevate-as-current-user:** Runs under user's own account (broader attack surface, use only when virtual account breaks compatibility).

### Rule Conflict Resolution
1. Deny rules always win
2. User-assigned rules beat device-assigned
3. Hash rules = most specific
4. Most attributes defined wins
5. Elevation type precedence: User-confirmed > Elevate-as-current-user > Support-approved > Automatic

### Certificate Rules — The Maintenance Trap
A certificate rule matches ANY file signed with that cert. Always pair with product name or internal name to narrow scope. Use reusable settings groups for centralized cert management.

### Known Issue
Windows Administrator Protection is mutually exclusive with Intune EPM on the same device. Check before deploying.

## Santa (macOS)

### Rule Precedence (first match wins)
CDHash → Binary → SigningID → Certificate → TeamID

### Policies
ALLOWLIST | ALLOWLIST_COMPILER (transitive, 6mo) | BLOCKLIST | SILENT_BLOCKLIST | CEL

### Client Modes
- Monitor: log only
- Lockdown: enforce
- Standalone: TouchID approval, creates local rule

### Deployment via Intune MDM
1. Deploy .pkg via LOB app
2. System Extension profile (Team ID: ZMCG7MLDV9, extension: com.northpolesec.santa.daemon)
3. PPPC profile (Full Disk Access + Notifications)
4. Santa config profile (com.northpolesec.santa)

### Best Practice
Use TeamID/SigningID rules, not binary hashes. Layer: TeamID allow + SigningID block = allow publisher but block specific app. Transitive allowlisting for developer compilers.

### Santa Limitations
- **Doesn't block scripts:** Shell, Python, Ruby scripts bypass Santa entirely. Only binary execution (execve) is blocked. Need CyberArk EPM or other controls for script execution.
- **Dynamic library limitation:** Doesn't protect against dlopen, DYLD_INSERT_LIBRARIES, or replaced libraries on disk. SIP protects against these when enabled.
- **CrowdStrike coexistence:** CrowdStrike Falcon for macOS uses same Endpoint Security Framework. Can coexist with Santa. Both use AUTH_EXEC for pre-execution blocking.

### Workshop by North Pole Security (Enterprise Santa)
- Commercial management platform built by the Santa team (original Google creators)
- Centralized rule management with sync protocol
- Approval workflows: self-service, designated approvers, social voting
- Risk engine: VirusTotal, ReversingLabs, custom webhook plugins
- Package rules: Homebrew, npm, Cargo, GitHub Releases, VS Code extensions, Terraform
- File access authorization (protect SSH keys, cookies, keychains)
- USB/SD blocking
- Telemetry with SQL queries + management zones + audit trails
- SOC 2 compliant
- Cloud-hosted or self-hosted
- Private sync protocol for faster feature delivery (Santa 2025.10+)
- Sandbox profiles (Santa 2026.5): confine allowed apps to least-privilege profiles
- $4M seed round from Andreessen Horowitz (2025)
- Pricing: commercial, contact for quote

### Santa + Workshop vs Other macOS Solutions
- **CrowdStrike Falcon:** EDR with some application control, but not dedicated binary authorization
- **Jamf Protect:** Apple-native EDR, some app blocking, not full binary authorization
- **Kandji:** MDM with app blocking, not full binary authorization
- **Airlock Digital:** Third-party app control that integrates with CrowdStrike
- **Verdict:** Santa + Workshop is the purpose-built enterprise answer for macOS binary authorization

## ASR (Attack Surface Reduction) Rules

### How ASR Complements WDAC
- WDAC = what runs (execution control)
- ASR = how it behaves (behavioral control)
- Even if a whitelisted app gets compromised, ASR blocks its risky behaviors
- ASR rules target: credential stealing, process injection, script execution, Office child processes

### Key ASR Rules
- Block credential stealing from LSASS (9e6c4e1f)
- Block Office apps from creating child processes (d4f940ab)
- Block JavaScript/VBScript from launching downloaded content (d3e037e1)
- Block untrusted/unsigned processes from USB (b2b3f03d)

### ASR Deployment
- Requires Microsoft Defender for Endpoint Plan 1/2
- Deploy via Intune Endpoint Security > Attack Surface Reduction
- Start in Audit mode, review events, then switch to Block
- Exclusions apply to ALL ASR rules (cannot exclude per-rule)


## Reference: enterprise-app-control-research.md

# Enterprise Application Control & Privilege Management — Research Bank

## Microsoft Licensing (as of July 2026)

### M365 E5 Includes (no additional cost)
- **Intune Plan 1** — full MDM/MAM for all platforms
- **Intune Endpoint Privilege Management (EPM)** — JIT elevation, support-approved workflows, Windows-only (rolling out July 2026)
- **Enterprise Application Management (EAM)** — Microsoft-hosted catalog of 1000+ prepackaged Win32 apps with auto-updates (GA July 2026, included in E5 starting July 1 2026)
- **Microsoft Cloud PKI** — cloud-based certificate management
- **Remote Help** — secure remote assistance
- **Advanced Analytics** — endpoint analytics and reporting
- **Defender for Endpoint P2** — EDR, attack surface reduction, threat intelligence
- **Entra ID P2** — PIM, Identity Protection, Access Reviews, Conditional Access
- **Windows 11 Enterprise E5**

### M365 E3 Includes (subset)
- Intune Plan 1
- Remote Help, Advanced Analytics, Intune Plan 2 (Tunnel for MAM, FOTA, Specialty Devices)
- Does NOT include: EPM, EAM, Cloud PKI

### Entra P2 (identity only — often confused with device management)
- PIM, Identity Protection, Access Reviews, Entitlement Management
- Does NOT include: Intune, WDAC management, EPM, EAM, any device controls

## WDAC (App Control for Business)

### Key Facts
- Kernel-level enforcement via ci.dll — cannot be disabled by local admin
- With HVCI, even kernel exploits can't modify active policy
- MSRC servicing criteria (treated as a security boundary) — AppLocker is NOT
- Active development; AppLocker is feature-complete (maintenance only)
- Multi-policy format: Win10 1903+, Server 2022+, up to 32 active policies
- Supplemental policies extend base without modifying it — independent lifecycle
- Deploy via ApplicationControl CSP (rebootless, multi-policy) — NOT AppLocker CSP (forces reboot, single-policy)
- Rebranded: Device Guard → WDAC → App Control for Business (Win11 22H2). Same ci.dll code path, three names in nine years.

### Rule Evaluation Order (Verified — Microsoft Docs 2026)
1. **Explicit DENY** — always wins, cannot be overridden by any allow rule or supplemental policy
2. **Explicit ALLOW** — base policy first, then supplemental policies (intersection for multiple base, union for base+supplemental)
3. **Managed Installer EA** — files tagged with `$KERNEL.SMARTLOCKER.ORIGINCLAIM` by trusted installer process
4. **ISG EA (cached)** — previously verified by cloud reputation, cached locally
5. **ISG cloud query** — queries Microsoft cloud for reputation (requires internet). Known-good = allow. Unknown = deny.
6. **Implicit DENY** — default block for anything not matched above

### Rule Types
- **Publisher/signer rules**: trust by code signing certificate. Survives app updates. PRIMARY rule type. ~80% of rules.
- **Managed installer**: auto-trusts apps deployed through Intune/SCCM. ~15% of rules.
- **Hash rules**: trust specific file version. Breaks on every update. Use only for unsigned tools. ~5% of rules.
- **Path rules**: trust everything in directory. Only for admin-only writable locations (Program Files, System32). NEVER user-writable dirs.
- **Deny rules**: explicit block. Always evaluated first. Cannot be overridden.

### Managed Installer Deep Dive
- Auto-trusts apps deployed through Intune/SCCM without explicit allow rules
- Uses NTFS Extended Attribute `$KERNEL.SMARTLOCKER.ORIGINCLAIM`
- Trust propagates down process tree (child processes of managed installer also get tagged)
- REQUIRES AppLocker policy for MI tracking (AppLocker CSP doesn't support ManagedInstaller rule collection — needs PowerShell script)
- **SCCM**: Defines CCMExec.exe + CCMSetup.exe as managed installers. EnforcementMode="Enabled" (generates 8004 Error events — false positives).
- **Intune**: Defines IME as managed installer. EnforcementMode="AuditOnly" (generates 8003 Warning events — false positives). Deployed via hidden Proactive Remediation. As of Aug 2025, supports per-group assignment (not just tenant-wide).
- **Verify EA**: `fsutil file queryea "C:\path\to\application.exe"` — look for `$KERNEL.SMARTLOCKER.ORIGINCLAIM`. First ULONG `01` = always present. Second ULONG `00` = managed installer, `01` = ISG. Third ULONG `00` = directly written by MI, `02` = child-of-child (NOT trusted).
- **Backlog problem**: only tags files installed AFTER policy active. Pre-existing apps need explicit rules. #1 gotcha.
- **Self-updating apps**: updates outside MI channel don't get tagged. Fix: publisher rules alongside MI.
- **Process tree breaks**: if installer spawns new parent process mid-install, files won't get tagged.
- **Intune abuse (CVE)**: IME `-PowerShell` parameter has command injection. Files written get MI trust. Can bypass WDAC + CLM. Fixed in newer IME versions.
- **File copy strips EAs**: Windows Explorer copy/paste breaks Extended Attributes. `robocopy.exe` preserves them.

### ISG (Intelligent Security Graph)
- Requires internet connectivity. Not for air-gapped or offline devices.
- Trust laundering: ISG-trusted apps can pass trust to arbitrary executables they write. Any standard user can download PuTTY (ISG-trusted), use its file browser to launch unsigned exe, and WDAC caches trust.
- Does NOT meet Essential Eight "organization-approved set" requirement (ISM-1657, ISM-1582). Not suitable for compliance-driven deployments.
- ISG + Managed Installer = dramatically increased trusted surface. Avoid in high-security environments.

### WDAC Gotchas
1. Signed base policies require reboot on Win11 <24H2 with HVCI. Deploy via script, not MDM.
2. 32 policy limit pre-April 2024 = bluescreen 0x3b. Apply April 2024 cumulative update.
3. PowerShell CLM breaks many scripts (blocks COM, Win32 API, Add-Type, reflection, DSC, XAML, class definitions). Deploy separately from binary enforcement.
4. OMA-URI 350KB limit. Use signer rules + MI, not hash rules.
5. Deny rules in supplemental policies are silently ignored. Supplements only ADD trust.
6. `Add-SignerRule` resets HvciOptions to 0. Always run `Set-HVCIOptions` after.
7. Empty deployed policy = nothing runs (including Windows).
8. Option 19 (Dynamic Code Security) always enforced in audit mode.
9. MSI files always detected as user-writable on Win10 and Server 2022 and earlier.
10. AppLocker doesn't enforce on services by default — needs RuleCollectionExtensions (no GUI option).
11. CA expiration (July 2025): 15-year Microsoft issuing CAs expiring. New handling logic auto-infers trust for new 2023/2024 CAs. No policy update needed. Opt out: "Disabled:Default Windows Certificate Remapping".

### WDAC Security Vulnerabilities (Verified)
- **CVE-2025-33069**: Improper cryptographic signature verification. CVSS 5.1. Fixed June 2025 Patch Tuesday. Affects Win11 24H2, Server 2025.
- **CVE-2025-59033**: Driver blocklist entries with FileAttribRef qualifier not blocked without HVCI. Microsoft disputes — states blocklist intended for HVCI.
- **CVE-2026-25166**: imgmgr.exe from Windows ADK bypasses WDAC via insecure deserialization. Not on Microsoft's block list yet.
- **EDR disabling attack**: Attackers with admin place crafted WDAC policy to disable EDR. Seen in wild (Beazley Security). MITIGATION: signed policies + HVCI.
- **IME command injection (CVE)**: Intune Management Extension `-PowerShell` parameter has command injection. Standard user can write files that get MI trust, bypassing WDAC + CLM. Files written by IME get `$KERNEL.SMARTLOCKER.ORIGINCLAIM` EA. Fixed in newer IME versions. MITIGATION: signed policies + HVCI.

### WDAC + ASR Integration
- WDAC = what runs (application allowlisting). ASR = how it behaves (behavioral rules).
- ASR rules target risky behaviors even from whitelisted apps (credential stealing, process injection, etc.).
- ASR event IDs: 1121 (block), 1122 (audit), 1129 (user override).
- ASR exclusions apply to ALL rules — can't exclude from one rule while keeping others.
- Deploy via Intune: Endpoint Security > Attack Surface Reduction. Start in Audit mode.
- Low-breakage rules (enable first): LSASS protection, USB block, Office child process block.
- High-breakage rules (audit 2 weeks first): Office macro block, script block.
- Included in M365 E5 (Defender for Endpoint P2). No additional cost.

### Audit Mode → Enforce Mode Transition Pattern
- **The #1 failure point**: teams rush to enforce without adequate baseline data.
- **Event IDs to monitor**: 3076 (WDAC audit), 8003 (AppLocker audit).
- **What to look for**: unsigned .exe in user-writable paths, signed apps from unknown publishers, scripts from user directories, quarterly/annual tools.
- **Audit duration**: 60-90 days minimum (insurance has quarterly/annual tools).
- **Validation checklist**:
  - Zero 3076/8003 events for 2 consecutive weeks
  - Publisher rules cover 80%+ of events
  - Managed Installer covers 15%+ of events
  - Hash rules cover <5% of events
  - IT pilot group tested for 2 weeks
  - Helpdesk has WDAC exception process
  - Rollback plan: audit mode policy ready to deploy

### Shared Workstations Pattern (Call Center)
- **The challenge**: 3 user roles on same device (Agent, Supervisor, Manager). WDAC is per-device (same rules for everyone). AppLocker is per-user (different rules per AD group).
- **The solution**: Layer WDAC + AppLocker.
  - Layer 1: WDAC (device-level) — what CAN run on this device. Kernel enforcement, can't be bypassed.
  - Layer 2: AppLocker (user-level) — who can run what. Agent group blocked from PowerShell. Manager group allowed.
  - CyberArk EPM: self-service elevation for Manager group.
- **Result**: same device, different capabilities per user role. Security follows the user, not the device.

### Developer Workstations Pattern
- **The challenge**: build tools compile unsigned code, package managers download binaries, Docker runs unsigned code inside, WSL runs Linux binaries (WDAC doesn't enforce).
- **The approach**: separate WDAC supplemental policy for dev workstations.
  - Allow build output directories (bin/, obj/, dist/)
  - Allow package manager binaries (npm, pip, cargo)
  - Allow Docker Desktop, WSL (container runtime is the trust boundary)
  - Santa transitive allowlisting on macOS (approved compilers auto-trust output for 6 months)
  - CyberArk EPM self-service elevation
  - Accept higher risk for dev workstations (developers are most productive when not fighting security tools)

### WDAC + ASR Integration
- WDAC = what runs (application allowlisting). ASR = how it behaves (behavioral rules).
- ASR rules target risky behaviors even from whitelisted apps (credential stealing, process injection, etc.).
- ASR event IDs: 1121 (block), 1122 (audit), 1129 (user override).
- ASR exclusions apply to ALL rules — can't exclude from one rule while keeping others.

### WDAC Deployment via Intune
- OMA-URI: `./Vendor/MSFT/ApplicationControl/Policies/{PolicyGUID}/Policy`
- Data type: Base64 (file). Rename `.cip` to `.bin` for upload.
- Intune built-in App Control uses legacy AppLocker CSP + single-policy format — use custom OMA-URI for multi-policy.
- Policies deployed via ApplicationControl CSP: removed on unenrollment but stay in effect until reboot. Deploy AllowAll.xml first, then delete.
- Policies deployed via AppLocker CSP: can't be deleted through Intune console. Deploy audit-mode policy or use script.

### WDAC + AppLocker Together
- When both configured, WDAC takes precedence for code types it covers. AppLocker rules for same code types ignored.
- AppLocker rules continue for code types WDAC doesn't cover or isn't configured for.
- AppLocker still useful for per-user/group rules on shared devices (WDAC is per-device only).
- AppLocker is NOT deprecated. "Feature complete, not actively developed, continues to receive security fixes."

### WDAC Policy Signing
- RSA 2K/3K/4K only. No ECDSA.
- SHA-256/384/512. SHA-256 only on devices without Nov 2022 cumulative update.
- PKCS 7 standard.
- Signed policy + HVCI = survives admin-equivalent attacker. Only config that gets MSRC CVE treatment.
- Always deploy unsigned version first. Enable Rule Options 9 (Advanced Boot Options) and 10 (Boot Audit on Failure) during testing.
- `Add-SignerRule` resets HvciOptions. Run `Set-HVCIOptions` AFTER signing rules.

### WDAC Policy Lifecycle (Microsoft Recommended)
1. Define circle of trust (what apps are allowed)
2. Build audit mode policy
3. Deploy to targeted devices (staged rollout)
4. Monitor audit events (Event ID 3076)
5. Iterate until block events match expectations
6. Deploy enforced policy (staged rollout)
7. Repeat whenever trust boundaries or app requirements change

### Essential Eight Compliance
- ML1: AppLocker sufficient
- ML2/ML3: WDAC required
- ISG does NOT meet Essential Eight (ISM-1657 "organization-approved set", ISM-1582 "annual validation")
- Script enforcement required for ISM-1657 (control PowerShell, VBScript, cscript, HSMTA, MSXML)
- Microsoft recommended application blocklist required for ML2
- Vulnerable driver blocklist required for ML3
- Central event logging required for ML2+

### MITRE ATT&CK Coverage
- M1038 (Execution Prevention): WDAC/AppLocker explicitly cited
- T1059 (Command and Scripting Interpreter): script enforcement
- T1553.002 (Code Signing Policy Modification): signed policies prevent tampering
- T1574 (Hijack Execution Flow): DLL side-loading blocked by signing enforcement
- T1195 (Supply Chain Compromise): signature verification catches tampered builds
- T1036 (Masquerading): publisher rules prevent impersonation

## AppLocker

### Key Facts
- User-mode enforcement via AppIDSvc service. NOT a security feature (Microsoft's words).
- Admin can bypass by stopping AppIDSvc or using TrustedInstaller token.
- Ignores processes with NT AUTHORITY\SERVICE (S-1-5-6) in token (requires admin to exploit).
- Per-user/group rules — THE reason to keep it alongside WDAC.
- GhostLocker PoC: dynamically generates prohibitive rules for security platform executables.
- Event IDs: 8003 (audit), 8004 (enforced block).
- By default, doesn't enforce on services. Needs RuleCollectionExtensions (no GUI option).
- Not deprecated. "Feature complete, not actively developed, continues to receive security fixes." KB5044288 (Oct 2024) fixed rule-merge bug.

### When to Use AppLocker
- Shared workstations needing per-user rules (call centers, branches, kiosks)
- Managed installer tracking (AppLocker provides MI policy, WDAC trusts the tags)
- .bat/.cmd script enforcement (WDAC doesn't enforce on cmd.exe)
- Migration path: `ConvertFrom-AppLockerPolicy` PowerShell cmdlet converts to WDAC

## Intune EPM

### Elevation Types
- **Automatic**: trusted apps, no prompt, silent elevation
- **User-confirmed**: right-click → confirmation. Optional: business justification, Windows auth
- **Support-approved**: user submits request → admin approves in Intune console → 24hr approval window → toast notification
- **Deny**: blocked entirely
- **Elevate-as-current-user**: runs under user's own account (preserves profile). Broader attack surface. Use only when virtual account causes failures.

### Rule Design
- Auto-updating apps (Chrome, Zoom): certificate + product name. NOT hash.
- Stable tools: certificate + product name + hash. Pins to reviewed version.
- High-risk admin tools: support-approved. Deny child processes.
- Default elevation response: Deny all requests or Require support approval. NEVER "user confirmed" alone (allows arbitrary elevation).

### Conflict Resolution
1. Deny always wins
2. User-assigned rules > device-assigned rules
3. Hash rules = most specific
4. Most attributes defined wins
5. Elevation type precedence: User-confirmed > Elevate-as-current-user > Support-approved > Automatic

### Gotcha
- Windows Administrator Protection is mutually exclusive with Intune EPM. If enabled, EPM elevations fail.
- EPM is Windows-only, 64-bit only (x64, ARM64). No macOS/Linux/servers.

## CyberArk EPM

### Capabilities
- Privilege management: Windows, macOS, Linux, servers
- Application control: allowlisting, blocking, default-deny, ringfencing
- Ringfencing: restrict what allowed apps can access (Files, Registry, Net shares, Net Objects, Memory of other processes, Network & Internet)
- Credential theft prevention: blocks Mimikatz, credential dumping
- Server: local admin password vaulting/rotation, JIT elevation for helpdesk
- Approval workflows: ServiceNow integration, multi-approver, time-boxed
- Cross-platform: Windows (full), macOS (app control + privilege mgmt), Linux (sudo elevation + app control)

### macOS Specifics
- System Extension + Network Extension installed during agent deployment
- Scripts enforced when executed directly (`./myscript.sh` or `bash ./myscript.sh`)
- Supported interpreters: /bin/bash, /bin/csh, /bin/ksh, /bin/sh, /bin/tcsh, /bin/zsh
- v26.5: macOS Script Validation via Team ID and Signing ID
- SIP monitoring: "Only elevate macOS applications if notarized by Apple or protected by SIP. Set Monitor SIP files to On."
- Homebrew issue: installation fails with EPM due to admin rights assumptions. Customized script needed.
- Mutual exclusions needed with other security tools (Defender, CrowdStrike, etc.)
- Agent 11.5+: `/Applications/CyberArk EPM.app`, `/Library/Application Support/CyberArk`

### Mutual Exclusions (Critical)
When running alongside other security agents (Defender, Intune EPM, etc.):
- Exclude from EPM: Defender platform path, IME path, CodeIntegrity path, EDR agent path
- Exclude EPM from others: `C:\Program Files\CyberArk\Endpoint Privilege Manager\Agent\*`, drivers (vfdrv.sys, vfnet.sys, vfpd.sys, CybKernelTracker.sys)
- macOS (Agent 11.5+): `/Applications/CyberArk EPM.app`, `/Library/Application Support/CyberArk`
- Developer source code directories, compiled output directories, frameworks, temp code/compilers

### Intune Integration
- "Exclude service accounts from access restrictions" setting must be DISABLED for Intune "Install as system" to work with EPM
- Without this, system-level processes bypass EPM policy evaluation

## Santa (macOS Binary Authorization)

### Key Facts
- Open source (Apache 2.0), originally built by Google for 100K+ Mac fleet
- Now maintained by North Pole Security (founded by Santa's original creators)
- Runs as macOS system extension using Endpoint Security framework
- Intercepts every execution (AUTH_EXEC) before code runs — only userspace mechanism for pre-execution blocking
- Rule precedence: CDHash → Binary → SigningID → Certificate → TeamID (first match wins)
- Policies: ALLOWLIST, ALLOWLIST_COMPILER (transitive, 6mo, machine-local), BLOCKLIST, SILENT_BLOCKLIST, CEL, Sandbox Profiles (2026.5)
- Client modes: Monitor (log only) → Lockdown (enforce) → Standalone (TouchID approval)
- Team ID: ZMCG7MLDV9

### Limitations
- **Does NOT block scripts** — shell, Python, Ruby scripts bypass Santa entirely. Santa only blocks binary execution (execve and variants).
- **Does NOT protect against dynamic libraries** — dlopen, DYLD_INSERT_LIBRARIES, replaced libraries on disk. SIP protects against these when enabled.
- **No driver control** — Santa doesn't control kernel drivers.
- **No ringfencing** (until 2026.5 sandbox profiles) — Santa blocks/allows execution but doesn't contain what allowed apps can do.

### Workshop by North Pole Security (Enterprise Management)
- Commercial management platform built by the Santa team (same team, same engine)
- Centralized rule management with sync protocol — push policy changes to all endpoints in seconds
- Approval workflows: self-service, designated approvers, social voting (same approach Google used for 100K+ Macs)
- Risk engine: VirusTotal, ReversingLabs integration — auto-screens unknown binaries before human review
- Package rules: auto-allowlist Homebrew, npm, Cargo, GitHub Releases, VS Code extensions, Terraform plugins
- File access authorization + USB/SD blocking — even if malware runs, it can't read SSH keys or exfiltrate via USB
- Telemetry with SQL queries + management zones + audit trails — query every execution event across the fleet
- SOC 2 compliant. Cloud-hosted or self-hosted.
- Private sync protocol (faster feature delivery than open-source sync servers)
- $4M seed round from Andreessen Horowitz (2025)
- Pricing: commercial, contact for quote
- Complements existing stack, doesn't replace it. Integrates alongside Jamf.

### Sandbox Profiles (2026.5 — NEW)
- New policy type alongside Allowlist/Blocklist/CEL
- Attach macOS sandbox (seatbelt) profile to a rule
- Target by Team ID, SigningID, or hash
- Confines allowed apps to least-privilege profile
- This is ringfencing for macOS — equivalent to CyberArk's ringfencing

### WDAC for macOS (Preview — 2026)
- Microsoft extended WDAC to macOS as part of Intune endpoint security
- Uses Endpoint Security Framework (ESF) — same as Santa and Jamf Protect
- Provides unified Windows/macOS application control policy framework
- As of 2026, still in preview. Less mature than Santa.
- Worth watching but Santa is the production-ready choice today.

### Deployment via Intune MDM
1. System Extension profile: Team ID `ZMCG7MLDV9`, extension `com.northpolesec.santa.daemon`, NonRemovable: true. Also allow `com.northpolesec.santa.netd` for network extension.
2. TCC profile: Full Disk Access for `com.northpolesec.santa.daemon`, `com.northpolesec.santa.netd`, `com.northpolesec.santa.bundleservice`
3. Notifications profile: alert + banner + sound for `com.northpolesec.santa`
4. Santa Configuration profile: ClientMode, EnableTransitiveAllowlisting, EventLogType
5. Deploy Santa .pkg via MDM (signed and notarized, suitable for direct deployment)
6. Deployment sequence: .pkg → profiles → baseline rules → build allowlists → pilot → expand

### Best Practices
- Prefer TeamID/SigningID rules (not binary hashes — break on every update)
- Transitive allowlisting for developers (mark Xcode as ALLOWLIST_COMPILER)
- Standalone mode for edge cases (TouchID approval, creates local rule)
- Layer: TeamID allow + SigningID block = allow publisher but block specific app
- Santa + CyberArk on macOS: Santa = what runs (execution control), CyberArk = what privileges + what access (privilege management + ringfencing)

### Apple's app.settings (macOS 27)
- New native MDM configuration for binary authorization
- `AllowedBinaries` / `DeniedBinaries` by CD Hash, Team ID, signing ID
- `AlwaysAllowManagedApps` auto-allows MDM-deployed apps
- Promising but unproven. Less flexible than Santa (no CEL, no transitive allowlisting, no file access auth).

## 3rd Party Alternatives

### BeyondTrust EPM
- Direct competitor to CyberArk. Same scope: privilege management + app control across Windows, macOS, Linux.
- Architecture: Azure SaaS or on-prem U-Series appliance. Agent + adapter. Adapter polls every 5min.
- Policy model: Workstyles + Power Rules (PowerShell-based). QuickStart templates.
- Cost: Custom pricing. Vendr benchmarks: $10-40/user/month. Median contract $17,795/year.

### ThreatLocker
- Modern app control + ringfencing in one product.
- Architecture: cloud portal + agent. Policies run top-to-bottom (firewall-style). Default deny.
- Ringfencing: per-app control of files, registry, network, other apps.
- 24/7 Cyber Hero team for policy tuning.
- Cost: Custom pricing. Vendr/Forrester benchmarks: $2-5/endpoint/month. Forrester TEI: $40.40/endpoint/year for 10K endpoints.

### CrowdStrike Falcon Application Control
- EDR + application control in one product. NOT a standalone app control tool.
- Best for: organizations already on CrowdStrike EDR that want integrated app control.
- Cost: $60-240/endpoint/year (Go $59.99, Pro $99.99, Enterprise $184.99).
- NOT a replacement for WDAC/AppLocker — complementary. CrowdStrike = detection, WDAC = prevention.
- macOS: CrowdStrike Falcon for macOS exists. Single lightweight agent. Can coexist with Santa (but network filter conflicts possible with Jamf Trust).

## Server Considerations

### WDAC on Servers
- Server 2016: single policy only, no managed installer, no ISG, no multi-policy
- Server 2019: managed installer + ISG, still single policy format
- Server 2022+: full multi-policy support, HVCI on by default for new installs
- HVCI not default on older servers — must be explicitly enabled
- Boot Audit on Failure (Option 10): ALWAYS enable on servers. Prevents bricking.
- Publisher rules for Microsoft workloads (SQL, Exchange, IIS)
- Server Core: limited GUI, use PowerShell for policy management

### CyberArk on Servers
- Local admin password vaulting: unique per server, auto-rotated
- JIT elevation for helpdesk access
- Credential theft prevention (Mimikatz blocking)
- Application control as complement to WDAC
- WDAC = what runs, CyberArk = who accesses + what it does

## macOS Platform Summary

### What Runs macOS App Control
- **Santa** (open-source): execution control, rule-based, Endpoint Security framework
- **CyberArk EPM** (commercial): privilege management + application control + ringfencing
- **WDAC for macOS** (preview): Microsoft's unified approach, not production-ready yet
- **Apple app.settings** (macOS 27): native MDM binary authorization, unproven

### Recommended macOS Stack
1. **Santa** — execution control (what can run). TeamID/SigningID rules, transitive allowlisting.
2. **CyberArk EPM** — privilege management (what privileges) + ringfencing (what access)
3. Together: Santa = gatekeeper, CyberArk = containment + privilege elevation


## Reference: enterprise-app-control-vendor-comparison.md

# Enterprise Application Control: Vendor Comparison & Portable App Governance

## Key Insight: Governance vs Security

**Governance** = controlling what users can run and what those apps can access. Discovery, graduated controls, identity-aware targeting, operational manageability, exception workflows.

**Security** = defending against sophisticated attackers. Kernel enforcement, tamper resistance, CVE-class boundaries.

Most enterprise application control discussions conflate these. They are different problems with different solutions.

## How Enterprises Actually Handle Portable/User-Context Apps

### The Problem
Portable apps install to `%USERPROFILE%` (user-writable) without admin rights. They bypass privilege management entirely. Tools like Claude, Cursor, and other Agentic AI can be installed this way.

### What Most Enterprises Do
- **Less than 15% of enterprises have application allowlisting enforced in block mode** (Decryption Digest, 2026)
- **Most enterprises use EPM tools** (CyberArk, BeyondTrust, Ivanti) for application control governance, not WDAC
- **WDAC is primarily used for compliance** (Essential Eight, CMMC, CIS) or as a defense-in-depth layer

### Why WDAC Can't Handle Portable Apps by Design
- WDAC refuses to create FilePath rules for user-writable directories (%TEMP%, %APPDATA%, %USERPROFILE%)
- This is a security feature — allowing execution from user-writable paths would let users drop and run arbitrary code
- Microsoft's own documentation: "Admin-write-only paths — By default, WDAC only allows FilePath rules pointing to locations that are writable exclusively by administrators"

## Vendor Approaches to Portable App Governance

### CyberArk EPM (Idira) — 3-Layer Framework
1. **Layer 1 — Risk-Reduction Controls**: Restricts all user-based apps from invoking sensitive OS components
2. **Layer 2 — Allowlist for Approved Apps**: Publisher + Location + Original Filename + Checksum
3. **Layer 3 — Discovery and Default-Deny**: Log first, then block unapproved apps

- Trusted Sources with Inherited Trust (equivalent to managed installer)
- Ringfencing: control what allowed apps can access (internet, intranet, registry, memory)
- Per-user targeting via AD/Entra ID groups
- Cross-platform (Windows, macOS, Linux)

### Ivanti Application Control — Trusted Ownership Model
- Any file placed by a trusted owner (SYSTEM, TrustedInstaller, Administrators) is allowed
- Anything introduced by a user is denied by default
- "A portable application is copied into the user profile. Ivanti blocks it because it is user-owned."
- Applies consistently across executables, DLLs, scripts, and MSI packages

### ThreatLocker — Hash-Based Detection + Ringfencing
- Uses hash-based detection to identify unpatched software, including portable apps
- Ringfencing™ to control how applications interact with files, registry, and network
- Learning Mode to automatically profile applications
- Does NOT automatically profile software in Desktop and Downloads folders
- Has portable app patch management (unique capability)

### BeyondTrust EPM — QuickStart Templates
- Identifies apps by publisher, file hash, version, file path, trusted ownership
- Specific documentation on AI agent control
- Can control which child processes an approved AI agent can start
- Can prevent AI agents from modifying sensitive system locations

### Carbon Black App Control — Updater Approval Rules
- Approves files installed by application updaters
- Live File Inventory and Baseline Drift Tracking
- Can track all files of interest on all computers all the time

## Common Pattern Across All Vendors

Every major EPM tool uses some form of "trusted ownership" or "provenance-based" control:
1. Trust software installed by trusted owners (SYSTEM, Administrators, deployment tools)
2. Block software introduced by users by default
3. Allow exceptions through approval workflows

This is fundamentally different from WDAC's approach (which can't handle user-writable paths).

## Does Any Vendor Offer Something Idira Can't Do?

**Short answer: No.** All major EPM tools handle portable apps the same way. The only notable difference:
- **ThreatLocker** has portable app patch management — can detect and patch portable apps that traditional tools miss. CyberArk EPM doesn't have this. But this is a patching capability, not an application control capability.

## Sources
- CyberArk Community: "EPM - How to Contain User-Based Applications"
- Ivanti: "Trusted Ownership vs Allowlisting: Modern Application Control"
- BeyondTrust: "Using Endpoint Privilege Management with local AI agents"
- ThreatLocker: Patch management capabilities documentation
- Decryption Digest: "Application Allowlisting Enterprise Guide 2026"
- Hidden Obelisk: "Detecting Portable and Unauthorized Software with PowerShell and GPO"


## Reference: osfi-b13-requirements.md

# OSFI B-13 Requirements for Application Control

## Overview
OSFI Guideline B-13 — Technology and Cyber Risk Management (effective January 1, 2024) applies to all federally regulated financial institutions (FRFIs) in Canada.

## Relevant Principles

### Principle 12: Cyber Security
- "Security defence controls should aim to be preventive, where feasible"
- "Designing application controls to contain and limit the impact of a cyber attack"
- "Implementing, monitoring and reviewing appropriate security standards, configuration baselines and security hardening requirements"
- "Deploying additional layers of security controls, as appropriate, to defend against cyber attacks"

### Principle 8: Change Management
- "Changes to technology assets in the production environment are documented, assessed, tested, approved, implemented and verified in a controlled manner"
- This applies to application control policy changes — CAB approval required

### Principle 9: Patch Management
- "Controlled and timely application of patches across its technology environment"
- Application control complements patching by limiting what can execute

## Key Requirements for Application Control
1. Preventive controls (not just detective)
2. Ongoing monitoring and review of policies
3. Documented risk-based decisions
4. Continuous improvement
5. Audit trail for compliance demonstrations

## Compliance Mapping
- WDAC/AppLocker → Principle 12 (preventive application controls)
- CyberArk EPM → Principle 12 (privilege management, containment)
- Exception workflow → Principle 8 (controlled change management)
- Audit logging → Principle 12 (monitoring and review)
- Quarterly policy review → Principle 12 (continuous improvement)


## Reference: portable-app-control-deep-dive.md

# Portable & Non-Admin-Installed Application Control — Deep Dive

## The Core Problem

Users download and run portable apps from user-writable locations (Downloads, AppData, Temp, Desktop, USB). These bypass managed deployment, need no admin rights, and are the primary malware vector.

**Critical insight: You CANNOT blanket deny execution from user-writable paths.** Chrome, Discord, Teams, VS Code, OneDrive, Slack, Spotify — all install to `%USERPROFILE%\AppData\Local\*`. Blocking this path breaks half the fleet. The approach must be smarter.

## What Actually Works

### Publisher Rules (Allow Signed Apps from Approved Vendors)
- Chrome installs to AppData but is signed by Google LLC — publisher rule allows it
- Teams installs to AppData but is signed by Microsoft — covered by DefaultWindows policy
- Publisher rules evaluate BEFORE path rules in AppLocker — signed apps from approved publishers are allowed even in user-writable locations
- Publisher rules survive app updates — no policy change needed

### Managed Installer (Auto-Trust Intune-Deployed Apps)
- Apps deployed through Intune are tagged with NTFS Extended Attribute
- WDAC with Option 13 recognizes these tags
- Any app deployed through Intune is automatically approved

### Deny Unsigned/Unknown Code
- The deny rules only catch code that ISN'T signed by an approved publisher AND ISN'T deployed through Intune
- This catches: unsigned malware, portable tools, scripts from Downloads/Temp

### CyberArk User-Based Application Containment Framework
Three-layer architecture specifically for this problem:

**Layer 1: Restrict sensitive OS access**
- Block ALL user-based apps from invoking PowerShell, cmd, WMI, registry editors
- Even if Chrome is compromised, it can't launch PowerShell
- Doesn't block the app from running — blocks it from dangerous capabilities

**Layer 2: Allowlist sanctioned apps**
- Define approved user-based apps by:
  - Location: `%USERPROFILE%` and subfolders
  - Publisher: signed apps from approved vendors
  - Original filename: metadata compiled into the app
  - Checksum: SHA-256 for unsigned apps

**Layer 3: Default-deny for unknown**
- Discovery mode first (log all user-based app launches)
- After discovery: enable default-deny
- Unknown apps silently terminated
- Logs update the allowlist

**Ringfencing (unique to CyberArk):**
- Even allowed user apps can be restricted:
  - Block internet access (prevent exfiltration)
  - Block network share access (prevent lateral movement)
  - Block access to sensitive files (prevent credential theft)
  - Block launching other applications (prevent app-hopping)

## What Gets Caught vs What Doesn't

### CAUGHT (blocked)
- Unsigned malware downloaded to Downloads
- Unsigned portable tools from USB
- Unsigned scripts in Temp
- Any unsigned code from user-writable locations

### ALLOWED (works normally)
- Chrome (signed by Google, in AppData)
- Teams (signed by Microsoft, in AppData)
- VS Code (signed by Microsoft, in AppData)
- Any app signed by an approved publisher
- Anything deployed through Intune

### NOT CAUGHT (limitations)
- Signed malware (rare — supply chain attacks)
- Apps from publishers not in your allowlist
- Admin can bypass AppLocker (user-mode)
- LOLBins (PowerShell, MSBuild, etc.) — mitigated by script enforcement + CLM

## AppLocker Rule Structure for Portable App Control

```
Executable Rules:
  ALLOW: Publisher = "O=MICROSOFT CORPORATION" (any product, any version)
  ALLOW: Publisher = "O=GOOGLE LLC" (any product, any version)
  ALLOW: Publisher = "O=ADOBE INC." (any product, any version)
  ALLOW: Path = %WINDIR%\* (Windows components)
  ALLOW: Path = %PROGRAMFILES%\* (admin-installed apps)
  ALLOW: Group = Administrators (break-glass)
  DENY:  Path = %USERPROFILE%\AppData\* (unsigned code from user profile)
  DENY:  Path = %USERPROFILE%\Downloads\* (unsigned code from Downloads)
  DENY:  Path = %TEMP%\* (unsigned code from Temp)
  DENY:  Path = %HOT% (removable media)
```

**Key:** AppLocker evaluates publisher rules BEFORE path rules. Signed apps from approved publishers are allowed even in user-writable locations. The deny rules only catch unsigned/unknown code.

## WDAC Rule Evaluation Order (Verified — Microsoft Docs 2026)

WDAC evaluates rules in this order. Once a file matches, evaluation stops:

1. **Explicit DENY** — always wins, cannot be overridden by any allow rule or supplemental policy
2. **Explicit ALLOW** — base policy first, then supplemental policies
3. **Managed Installer EA** — files tagged with `$KERNEL.SMARTLOCKER.ORIGINCLAIM` by trusted installer process
4. **ISG EA (cached)** — previously verified by cloud reputation, cached locally
5. **ISG cloud query** — queries Microsoft cloud for reputation (requires internet). Known-good = allow. Unknown = deny.
6. **Implicit DENY** — default block for anything not matched above

This means: Publisher rules (explicit allow) evaluate BEFORE managed installer. Managed installer evaluates BEFORE ISG. Deny rules always win regardless.

Source: Microsoft Learn "App Control Admin Tips & Known Issues" (2025-03-20)

## WDAC Approach (Different Model)

WDAC doesn't focus on blocking by path — it focuses on allowing by publisher/managed installer. Everything not trusted is blocked by default (implicit deny).

- **WDAC enforces admin-write-only for path rules.** It won't let you create a path rule for a user-writable directory (by design — it would be a security hole).
- **Managed installer** auto-trusts Intune-deployed apps
- **Publisher rules** auto-trust approved vendors
- **Script enforcement** + PowerShell CLM

## Sources
- CISA CM0101: Block Applications in Writable Locations using AppLocker
- CyberArk Community: EPM - How to Contain User-Based Applications (2026-04-29)
- Microsoft Learn: App Control and AppLocker Overview (2026-03-29)
- Microsoft Learn: Essential Eight Application Control
- Decryption Digest: Application Allowlisting Enterprise Guide 2026
- cr0x.net: App Control / WDAC Lite: Practical Allow-Listing for Normal People


## Reference: pptx-layout-pitfalls.md

# PPTX Layout Pitfalls (July 2026)

## fit:'shrink' Doesn't Work in PowerPoint
PptxGenJS's `fit: 'shrink'` option sets "Shrink text on overflow" in PowerPoint, but PowerPoint doesn't apply it until you edit the text. LibreOffice applies it correctly.

**Fix:** After generating PPTX with PptxGenJS, re-save via LibreOffice headless:
```bash
libreoffice --headless --convert-to pptx /tmp/input.pptx --outdir /tmp/output/
```
This triggers the shrink behavior. Then copy the LibreOffice-processed file to the user.

**Source:** PptxGenJS issues #330, #544, #779, #991

## LAYOUT_16x9 vs LAYOUT_WIDE
- `LAYOUT_16x9` = 10" × 5.625" (standard PowerPoint)
- `LAYOUT_WIDE` = 13.33" × 7.5" (widescreen)
- If element coordinates are designed for 13.33×7.5 but you use LAYOUT_16x9, elements will go off the slide. Always match layout to coordinates.
- **Root cause of repeated cutoff:** Using LAYOUT_16x9 with coordinates designed for LAYOUT_WIDE causes elements at y=6.85 to be 1.2" beyond the old slide boundary.

## Boundary Validation
Add a post-generation validation that checks all elements fit within slide boundaries:
- y + h <= slide height (7.5 for LAYOUT_WIDE)
- x + w <= slide width (13.33 for LAYOUT_WIDE)
- Log warnings for violations, auto-clamp if needed
- **Don't over-clamp** — if validation makes elements too small, the real fix is to split content across multiple slides, not to shrink everything.

## Vertical Centering
When content doesn't fill the slide, don't just add `_yShift` to all elements — this causes inconsistent positioning. Instead:
1. Calculate the actual content height (last element Y+H - first element Y)
2. Calculate the shift: (slide_height - content_height) / 2
3. Apply the shift to all body elements, keeping footer/accent bar fixed

## User Corrections on Layout
- "stuff is cutoff" → check y+h <= slide height for all elements
- "not using the space effectively" → content is too small, increase font sizes or split across more slides
- "presentation goes off the slide" → elements positioned beyond slide boundaries, not just text overflow
- "some of them arent using the space effectively now though just being small" → validation clamping made elements too small, better to split content across multiple slides

## Visual QA Workflow
```bash
# Render PPTX to PDF
libreoffice --headless --convert-to pdf file.pptx --outdir /tmp/slides/
# Convert PDF pages to PNG
python3 -c "
import fitz
doc = fitz.open('/tmp/slides/file.pdf')
for i, page in enumerate(doc):
    page.get_pixmap(dpi=150).save(f'/tmp/slides/slide_{i+1:02d}.png')
"
# Check each slide with vision_analyze
```
Ask: "Is all content fully visible? Any cutoff, overlap, or text issues?"


## Reference: strategy-document-notes.md

# Enterprise IT Strategy Document Notes

### Original skill body: Enterprise IT Strategy Documents

Create strategy/comparison documents and presentations for enterprise IT decisions — security tools, implementation approaches, vendor comparisons, roadmaps.

## Document Structure Patterns

### For Technical Audiences (Desktop Engineering, Cybersecurity)
- Lead with the problem, not the solution
- Be honest about what breaks — don't oversell
- Show how tools actually work day-to-day, not just feature lists
- Include gotchas and known issues
- Show exception workflows and escalation paths
- Enterprise-specific considerations: change management, co-management, legacy apps, shared devices, regulatory requirements

### For Executive Audiences (CISO, IT Director)
- Lead with the recommendation, then justify
- Cost/benefit framing
- Risk & mitigation table
- Timeline with clear phases
- "What do we already have" vs "what do we need to buy"
- Regulatory backing (OSFI B-13, NIST, CIS, etc.)

## Critical Writing Rules

### "WHY This Matters" Context (Mandatory)
Every feature or capability listed in the document MUST include context about WHY it matters, not just WHAT it does. The audience may not know the tool — explain the value it provides. Examples:
- ❌ "Intelligent Security Graph (ISG) reputation"
- ✅ "Intelligent Security Graph (ISG) — Microsoft's cloud reputation service. WHY: auto-trusts known-good software (Chrome, Zoom, etc.) so we don't manually allowlist every app. Saves hundreds of hours of policy maintenance."
- ❌ "Publisher rules (certificate-based)"
- ✅ "Publisher rules (certificate-based) — allow all versions of software from a trusted publisher. WHY: when Adobe ships a new Acrobat, the publisher rule still covers it. Hash rules would break on every update."

### Stay Focused on the Problem Domain
If the user asks about a specific problem (e.g., portable app control), don't expand into tangential topics. Stay focused on:
- The specific problem being solved
- The tools that directly address it
- The implementation approach for that specific problem

Don't drift into: privilege management, password vaulting, compliance mapping, organizational process, stakeholder RACI, risk assessment — unless the user explicitly asks for these.

### Implementation Story, Not Configuration Details
The audience wants to understand HOW you actually roll something out across an enterprise, not the XML/payload/registry/OMA-URI specifics. Focus on:
- Discovery → Build Policies → Pilot → Rollout → Operate
- What breaks and how to handle it
- What changes by platform (Windows, macOS, servers)
- Exception workflows and escalation paths
- Monitoring and quarterly review cycles

Configuration details (XML schemas, OMA-URI paths, registry keys, config profile payloads) belong in implementation guides, not strategy documents.

### Autonomous Verification Workflow
When using MCP/Exa to verify technical claims in documents:
- Continue autonomously through ALL claims without pausing to report partial results
- Don't stop every 5 lookups to report — batch the entire verification
- Report the full verification summary at the end
- If new findings are relevant to the problem domain, add them to the document
- If new findings are tangential, note them but don't add them

### Anti-Patterns to Avoid
- **Don't include "we evaluated X and it's the same"** — either find genuinely unique alternatives or remove the section entirely
- **Don't blanket-recommend blocking user-writable paths** — explain that publisher rules must come first, deny rules only catch unsigned/unknown
- **Don't present feature comparison tables without implementation context** — how it works day-to-day matters more than feature checkboxes
- **Don't use vague "audit first" language** — specify audit period length (30/60/90 days), what events to collect, what gates to check before enforcing
- **Don't include filler** — if the audience already knows something, don't explain it

## Key Technical Patterns

### Application Control Layered Approach
The correct model for enterprise application control:
1. **Publisher rules** — allow signed apps from approved vendors (Google, Microsoft, Adobe). These match first and survive app updates.
2. **Managed installer** — auto-trust apps deployed through Intune/SCCM. Eliminates per-app allowlisting.
3. **Deny unsigned/unknown** — block executables not signed by approved publishers and not deployed through management tools.
4. **Containment** — ringfence allowed apps (restrict network, file, registry access).

**Critical insight:** You CANNOT blanket-block user-writable paths (AppData, Downloads, Temp). Chrome, Teams, VS Code, OneDrive all install to AppData. Publisher rules must evaluate BEFORE path deny rules.

### Enterprise-Specific Considerations
- **Audit period:** 60-90 days (not 30) to capture quarterly/annual finance tools
- **Legacy/unsigned apps:** Hash rules with expiration dates. Push dev teams to sign code.
- **Shared workstations:** Per-user rules (AppLocker) for call centers, branches, kiosks
- **Co-management:** Managed installer must cover both SCCM CCMExec and Intune IME
- **Change management:** CAB approval, 2-week advance notices, formal escalation
- **Timeline:** 12-24 months for full fleet (not 6-12)
- **Regulatory:** OSFI B-13 (Canadian financial), NIST, CIS, Essential Eight

## PptxGenJS Table Gotchas

When building comparison tables with `mkRow()` helper, the `cols` parameter MUST be a flat array of strings, never nested arrays. Nested arrays cause `Unexpected token ')'\"` syntax errors.

```javascript
// ✅ CORRECT
mkRow("Feature", ["Col1 text", "Col2 text", "Col3 text"])

// ❌ WRONG — causes syntax error
mkRow("Feature", ["Col1 text", ["Col2 text"], ["Col3 text"]])
```

## Workflow for Iterative Document Refinement

When the user asks for a strategy document:
1. Research the domain thoroughly (MCP/Exa for current info)
2. Create first draft at appropriate depth level
3. Present and ask for feedback on depth/scope
4. Iterate based on feedback — users will correct:
   - Too high-level → add implementation detail
   - Too technical → simplify to concepts
   - Too much filler → cut to substance
   - Wrong framing → adjust for audience
5. Infer from user's edits to the document what they actually want
6. When user edits the .pptx directly, read back changes with markitdown to understand their preferences

## Visual QA for Presentations

After building a .pptx, convert to images and visually inspect for issues:
1. Convert PPTX → PDF via LibreOffice headless: `libreoffice --headless --convert-to pdf file.pptx`
2. Convert PDF → PNG via PyMuPDF: `fitz.open(pdf); page.get_pixmap(dpi=150).save(slide.png)`
3. Use `vision_analyze` on each slide to check for: overlapping text, text cut off at edges, text too small to read, uneven spacing
4. Fix issues, re-render, re-verify
5. Common issues: bullet list containers too short for content (increase height), table rows too narrow for long text (increase rowH), footer bars overlapping with content above (move footer down)

## References

- application-control-domain.md — WDAC, AppLocker, CyberArk EPM, Intune EPM, Santa architecture details
- osfi-b13-requirements.md — Canadian financial regulatory requirements for technology/cyber risk
- `the Presentation Visual QA section of this skill's SKILL.md` — LibreOffice + PyMuPDF workflow for visual QA of presentations
