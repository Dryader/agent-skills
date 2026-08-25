---
name: enterprise-application-control
description: >
  Enterprise application control and privilege management — WDAC, AppLocker, CyberArk EPM,
  Intune EPM, Santa (macOS). Covers allowlisting, portable app control, managed installer,
  per-user rules, and privilege management across Windows clients, servers, and macOS.
  Use when discussing application allowlisting, blocking portable/non-admin-installed apps,
  WDAC vs AppLocker, or endpoint privilege management in enterprise environments.
triggers:
  - WDAC
  - AppLocker
  - App Control for Business
  - application allowlisting
  - application control
  - portable apps
  - managed installer
  - CyberArk EPM
  - Intune EPM
  - Santa macOS
  - binary authorization
  - privilege management
  - least privilege
  - endpoint security
  - portable app discovery
  - KQL portable apps
  - MDE hunting portable
  - shadow IT discovery
  - portable exe detection
  - FileProfile KQL
  - provenance-based detection
  - portable app discovery
  - KQL portable apps
  - MDE hunting portable
  - shadow IT discovery
  - portable exe detection
  - FileProfile KQL
tags: [security, windows, endpoint, app-control, enterprise]
---

# Enterprise Application Control

## When to Use

Use this skill when the user is discussing:
- Blocking or controlling portable/non-admin-installed applications
- WDAC (App Control for Business) vs AppLocker
- Application allowlisting in enterprise environments
- Managed installer configuration (Intune/SCCM)
- CyberArk EPM, Intune EPM, or Santa for macOS
- Per-user rules on shared workstations
- OSFI B-13 or similar compliance requirements for application control

## Key Concepts

### WDAC = App Control for Business
Same thing, rebranded in Windows 11 22H2. PowerShell cmdlets still say `WDAC`, event logs say `CodeIntegrity`. Microsoft's strategic direction for application control.

### WDAC vs AppLocker — The Real Difference
- **WDAC:** Kernel-level enforcement (ci.dll). Cannot be disabled by local admin. With HVCI, even kernel exploits can't modify policy. Per-device only (no per-user rules).
- **AppLocker:** User-mode enforcement (AppIDSvc). Admin can stop the service and bypass. Per-user/group rules (unique capability). Feature-complete (no new development).
- **Use both:** WDAC for kernel enforcement + AppLocker for per-user rules on shared devices. AppLocker also provides the plumbing for WDAC's managed installer feature.

### Managed Installer — The Game-Changer
Auto-trusts apps deployed through Intune/SCCM without explicit allow rules. Reduces policy maintenance by 80-90%.

**How it works:**
- Intune/SCCM process is designated as "managed installer" in AppLocker policy
- When MI writes files to disk, Windows tags them with NTFS Extended Attribute `$KERNEL.SMARTLOCKER.ORIGINCLAIM`
- WDAC Rule Option 13 tells WDAC to trust files with this EA
- Trust propagates down process tree (child processes also get tagged)
- Verify: `fsutil file queryea "C:\path\file.exe"` — look for `$KERNEL.SMARTLOCKER.ORIGINCLAIM`

**EA values (from fsutil output):**
- Second ULONG `00` = managed installer, `01` = ISG
- Third ULONG `00` = directly written by MI (trusted), `02` = child-of-child (NOT trusted)

**Critical gotchas:**
- Only tags files installed AFTER policy active (the "backlog problem") — #1 gotcha
- Self-updating apps (Chrome auto-update) — updates outside MI channel don't get tagged
- Process tree breaks — if installer spawns new parent process, files won't get tagged
- File copy strips EAs — Windows Explorer copy/paste breaks them. `robocopy.exe` preserves them.
- AppLocker CSP doesn't support ManagedInstaller rule collection — requires PowerShell script
- SCCM: CCMExec.exe + CCMSetup.exe. EnforcementMode="Enabled" (8004 Error events — false positives)
- Intune: IME only. EnforcementMode="AuditOnly" (8003 Warning events — false positives). Deployed via hidden Proactive Remediation. As of Aug 2025, supports per-group assignment.
- Intune abuse: IME `-PowerShell` parameter had command injection vulnerability. Files written get MI trust. Fixed in newer versions.

### Publisher Rules vs Hash Rules
- **Publisher rules:** Survive app updates. Cover all versions from same vendor. Primary rule type.
- **Hash rules:** Break on every update. Use only for unsigned internal tools. Track with expiration dates.
- **Path rules:** Only for admin-only writable locations. NEVER user-writable dirs (WDAC enforces admin-write-only for path rules).

### The "You Can't Just Block AppData" Problem
Blanket blocking `%USERPROFILE%\\AppData\\*` breaks Chrome, Teams, VS Code, OneDrive, Slack, Spotify, and dozens of legitimate apps. The approach is: publisher rules allow signed apps from approved vendors (match BEFORE path deny rules), deny rules catch unsigned/unknown code.

### Per-User Rules (Shared Workstations)
WDAC enforces per-device only. AppLocker is the ONLY tool with per-user/group rules. Essential for call centers, branches, kiosks where multiple users share devices with different permission levels.

### Enterprise-Specific Considerations
- **Legacy/unsigned apps:** Financial services, insurance, healthcare have lots of old internal apps. Need hash rules with expiry dates.
- **Shared workstations:** Call centers, branches need per-user rules (AppLocker).
- **Quarterly/annual tools:** Finance, audit tools won't appear in 30-day audit. Use 60-90 day audit period.
- **SCCM + Intune co-management:** Managed installer needs to cover both during transition.
- **Change management:** CAB approval, 2-week advance notices, formal escalation.
- **Regulatory:** OSFI B-13 (Canadian financial), Essential Eight (Australian), NIST.

## Portable App Discovery (Pre-Enforcement Phase)

Before you can enforce anything, you need to know what's out there. The user has
explicitly rejected exclusion-list-based approaches ("spaghetti code exclusion") in
favor of elegant, principle-based methods that scale without maintenance burden.

### Provenance-Based Discovery (Preferred)

Instead of filtering OUT known-good software, filter IN files introduced by the user.
MDE's `DeviceFileEvents` table captures BOTH download origin (`FileOriginUrl` from
Zone.Identifier ADS) AND the creating process (`InitiatingProcessFileName`).

**The core join:**
```
DeviceFileEvents (FileCreated by chrome/firefox/outlook/7z/explorer)
    ↓ INNER JOIN on (DeviceName, SHA1)
DeviceProcessEvents (actually executed from user-writable paths)
    ↓
Candidates — no exclusion lists needed
```

**Five independent provenance signals (all MCP-verified, July 2026):**
1. `FileOriginUrl` — Zone.Identifier HostUrl. Populated by Edge, Chrome, Firefox, Outlook, Office, WinRAR. NOT by 7-Zip (strips MOTW).
2. `InitiatingProcessFileName` — which process CREATED the file. Browsers/email/tools = user-introduced. SYSTEM/msiexec = deployed.
3. `ProcessIntegrityLevel` = "Low" — Windows kernel detected MOTW at execution time. FREE signal in DeviceProcessEvents.
4. Anti-join with `DeviceTvmSoftwareInventory` — file NOT in Defender's known-software inventory = invisible to Vuln Mgmt.
5. SmartScreen events (`SmartScreenAppWarning` / `SmartScreenUserOverride`) — user clicking through SmartScreen is strongest possible provenance signal.

**Two-score model — Portability + Risk (user correction, do NOT revert to composite risk scoring):**
First attempt used a single weighted composite (path × persistence × prevalence × trust). It buried known portable apps — a mouse jiggler with GlobalPrevalence 665K scored 1.98 because trust=0 cancelled path risk. "Safe" ≠ "not portable." Discovery is NOT risk scoring.
- **Portability (0-10)** — how confident this is a portable app: path base (×0.5) + provenance signals (0-2 each) + not-in-TVM + usage frequency. Sort by this.
- **Risk (0-10)** — how worried to be: unsigned/low prevalence, SmartScreen override, Defender alerts, network activity, script parent. Review by this.
- Buckets: Portable+Risky / Portable / Risky / Low signal. Output ONE merged CSV with a Bucket column (user prefers merged output, not multiple files).
- **NO decision tracking in the script** (user rejected twice): no Decision/Status columns, no decisions CSV param. Script outputs the scored inventory; vetting/approval is handled in the user's separate governance process.
- Do NOT propose internal-app exception lists that require hashes the user doesn't have.
- **Exploratory questions ≠ feature requests.** When the user asks "can this classify X?" or "does this handle Y?", they are often probing — answer the question first. Do NOT implement a feature in response to a question; the user will say "i dont know the hashes, was just asking, undo plz" (actual quote, July 2026).
- **Keep the artifact set minimal and each file's role obvious.** When a third file was added, the user asked "why do we have 2 kql queries now" — confusion is a signal of proliferation. Name files by goal (provenance.kql = discovery, provenance-governance.kql = vetting, provenance-full.kql = deep-dive) and state the role of each in one line when delivering.
- **DISCOVERY vs GOVERNANCE query shapes:** the provenance gate is precise but INCOMPLETE for vetting (misses pre-window files, unlisted extractors, share/USB copies, installers). For "vet/approve everything" runs use a completeness-first governance query (path-based, vendor-noise pre-filter only, installers INCLUDED) — provenance becomes a scoring signal, not a filter. Full table in portable-app-discovery-pipeline.md.
- **Extra risk signals (added July 2026, all free — columns already in KQL output):**
  - **Renamed binary (T1036.003):** compare PE `OriginalFileName` vs actual `FileName`. Renamed LOLBin (certutil, powershell, rundll32, mshta, wscript, cscript, regsvr32, msbuild, psexec, bitsadmin, wmic, cmd...) = +5 risk (defense evasion). Renamed regular tool (putty.exe → tool.exe) = +1 risk. MCP-verified pattern used by APT groups (Lazarus, APT32, menuPass).
  - **Command-line patterns** (ExampleCommandLine): download cradles (`certutil -urlcache`, `bitsadmin /transfer`, `Invoke-WebRequest`, `iex`) = +3; encoded commands (`-enc`, base64) = +3; LOLBin invocation (`rundll32`, `mshta`, `regsvr32 /s`) = +2.
  - **Persistence (T1547.001/T1053.005):** HKLM Run/RunOnce registry values + `schtasks /create` pointing at user-writable paths referencing a candidate = +4 risk. KQL joins available in provenance-full.kql. CAVEAT: MDE Advanced Hunting tracks HKLM ONLY — HKCU Run keys are invisible (confirmed by Microsoft Q&A).
  - **Metadata spoofing (T1036.001):** CompanyName claims Microsoft/Google/Adobe but file is NOT signed = +4 risk (`SPOOFED_METADATA`). Regin/BADNEWS pattern; free check in PowerShell.
  - **Office macro drops (T1137.001):** Office apps (winword/excel/powerpnt) as file creators = +3 risk (`OFFICE_DROP`) AND +3.0 portability. Spear-phishing pattern (FIN7/AgentTesla/PlugX).
  - **DLL sideloading (T1574.002):** candidate loads unsigned DLLs from its own directory = +3 risk (`SIDELOAD_DLL`). Candidate-scoped only; fleet-wide is an Electron FP magnet.
  - **AI tool detection (shadow AI):** FileName/CompanyName/ProductName match against known AI tool names (claude, codex, cursor, copilot, ollama, openclaw...) = `AI_TOOL` flag, ZERO risk change — governance conversation, not malware. MDE's native `AIAgentsInfo` table is prerelease; name-list is the today-version.
  - **Non-standard ports:** TopDestPorts outside {80,443,53,8080} = +1 (`NONSTD_PORT`). Cheap beaconing proxy.
  - **Initiator classes:** KQL `case()` classifies creators as Browser/Email/Archive/OfficeMacro/ScriptHost/Explorer — per-class portability boosts, OfficeMacro/ScriptHost catch previously-invisible droppers.
  - **Packer detection is a dead end in AH** — MDE doesn't expose PE sections/entropy; run packdetect/sigcheck at review time instead.
  - **Flags column:** every score is explainable — the script appends flag strings (RENAMED_LOLBIN:certutil.exe, ENCODED_CMD, PERSISTENCE...) per row so reviewers see WHY a file scored high without reverse-engineering the math.
  - **When everything lands in one tier, re-evaluate the model — don't tune thresholds.** The "everything Tier 3" failure was the risk-weighted composite burying safe-but-real portable apps; the fix was splitting Portability from Risk, not adjusting weights.

**FileProfile() enrichment via Advanced Hunting API:** cap is 1,000 per invoke. Use lightweight `datatable(...) | invoke FileProfile(...)` queries that complete in seconds (no DeviceProcessEvents scan). The heavy lifting (provenance join + aggregate) runs once in the AH portal; enrichment is server-side lookups.

**Critical KQL optimizations for 15k+ device fleets (all MCP-verified):**
- `hint.shufflekey = SHA1` on high-cardinality aggregations — prevents single-node bottleneck
- Use `has` (indexed) not `contains` (substring scan) for path matching
- 30-day query windows max — 90-day scans hit the 10-minute AH timeout
- Time-filter the `DeviceFileCertificateInfo` join to avoid explode
- `DeviceTvmSoftwareInventory` is NOT available in Sentinel — run in Defender XDR AH

**What this automatically excludes (no lists needed):**
- Everything deployed via Intune/SCCM (SYSTEM/msiexec-created — not in initiator filter)
- Everything auto-updated (Teams→Teams, Chrome→Chrome — no browser initiator, no FileOriginUrl)
- One-shot installers (DistinctDays ≤ 1 filter)

Complete KQL queries (three versions: full provenance, Sentinel-compatible, FileProfile preview),
PowerShell enrichment pipeline (three modes: AH API / Offline / SingleFile), and scoring formulas
are in portable-app-discovery-methodology.md.

### PowerShell + MDE API Engineering Pitfalls (learned the hard way, July 2026)

- **NEVER embed KQL inside a PowerShell here-string.** Kusto verbatim strings use `@"..."@` which
  collides with PowerShell's `@"..."@` heredoc — the parser dies with cascading errors (55 parse
  errors once). KQL goes in a separate `.kql` file loaded via `[IO.File]::ReadAllText()` — this is
  exactly what Microsoft's official MDE API sample does. This was the root cause of an hour of
  debugging.
- **`PSParser::Tokenize` does NOT throw** on syntax errors — it populates an errors ref array.
  Passing `[ref]$null` gives a false "clean" result. Always pass `[ref]$errors` and check the count.
- **Trailing comma on the LAST param in a param block** (before `)`) causes cascading parse errors
  that point at unrelated lines (e.g. `} catch {`). The errors never point at the real culprit.
- **`Write-Host "... ($var with words)..."` breaks the parser** — `$var` followed by `( with words)`
  reads as `$()` subexpression syntax. Use format strings: `("... {0} ..." -f $var)`.
- **Multi-property descending sort needs hashtables:** `Sort-Object A -Descending, B -Descending`
  is invalid. Use `Sort-Object @{Expression="A";Descending=$true}, @{Expression="B";Descending=$true}`.
- **Microsoft's official MDE API patterns** (from run-advanced-query-sample-powershell):
  `[Ordered]` hashtable for the OAuth body, `ConvertTo-Json -InputObject @{Query=$kql}` for the
  query body, `Invoke-WebRequest` + `ConvertFrom-Json` for responses. Token resource must be
  `https://api.securitycenter.microsoft.com` even when calling `api.security.microsoft.com`
  (audience mismatch = 403).
- **Auth without app registration:** `Connect-AzAccount` then `Get-AzAccessToken -ResourceUrl
  "https://api.securitycenter.microsoft.com"` works using Az's built-in enterprise app (present in
  every tenant). `az account get-access-token --resource ...` likewise. Az.Accounts 5.x returns
  SecureString — unwrap via `[System.Net.NetworkCredential]::new('', $token).Password`.
  `az login` can fail on work laptops with certificate issues; Connect-AzAccount is the fallback.
- **When incremental patching keeps failing, rewrite the file cleanly** with write_file instead of
  continuing to patch. The fuzzy patch tool struggles with PowerShell files (backticks, string
  interpolation, prior edits shifting line numbers) — repeated failures are the signal to stop
  patching.

### Legacy Approach (Exclusion-Based — Fallback Only)

The original method scanned all DeviceProcessEvents from user-writable paths and filtered
OUT known vendors via `ProcessVersionInfoCompanyName` exclusion lists. This approach
requires ongoing maintenance and is NOT recommended. The provenance-based method above
replaces it entirely.

## Documentation Preferences (User-Specific)

When writing documents for this user:
- **Tone:** Discussion between desktop engineering and cybersecurity teams. Not executive, not nitty-gritty. Engineer-to-engineer.
- **Depth sweet spot:** Explain HOW things work (mechanisms, tradeoffs, operational model), not HOW TO CONFIGURE them (XML, registry keys, OMA-URI, payload IDs). The user explicitly rejected nitty-gritty config details but wants technical substance.
- **No filler:** Don't repeat the same points in different sections. Don't add "bottom line" or "key takeaway" callouts that restate what's already said.
- **Don't mention evaluating alternatives that don't add value.** If ThreatLocker/BeyondTrust offer the same capabilities as the existing stack, just remove them entirely. Don't say "we evaluated X and decided against it."
- **Server and macOS coverage must be substantive.** Not just "what changes" — explain how the tools work on each platform, what's different, what the gotchas are.
- **Include comparison tables** — tool-by-tool comparison tables are very effective for understanding technical differences across enforcement model, bypassability, per-user rules, rule types, etc.
- **Standard sections for enterprise docs:** Tool comparison, per-tool deep dive, implementation overview, operations (exception workflow, monitoring, quarterly review), stakeholder RACI, risk assessment, OSFI/compliance mapping, open questions.
- **Ask questions before assuming** — don't assume licensing, existing tooling, or fleet composition.
- **Infer from context** — if the user edits the document, infer their preferences from the changes.
- **Iteration pattern:** User oscillated 8+ times between "too high-level" and "too nitty-gritty." Final sweet spot: mechanisms + gotchas + operational model, skip the config.
- **No exclusion-list spaghetti:** User rejects approaches built on maintained exclusion lists (vendor names, known-good paths, AppData folder allowlists, process-name filters). Prefer principle-based, provenance-based, or signal-based approaches that work without ongoing manual curation. Filter IN what you want, not OUT what you don't. If you find yourself building a list, stop — there's a better approach.
- **MCP-verify claims:** When presenting KQL optimizations, API limits, table schemas, or capability claims, verify against Microsoft documentation via MCP web search before asserting them as fact. The user will push back on unverified claims.
- **Be comprehensive when asked:** When the user asks "what about X?" or "why not add Y?", don't argue against adding it — add it if it fits. Err on the side of comprehensiveness over minimalism.
- **Bulk deck updates: verify EVERY deliverable.** When the user asks to remove a product/reference from all presentations (e.g. "remove Intune EPM from everything"), files regenerated AFTER the instruction are clean, but older files generated before it keep stale content. Scan every .pptx in Downloads (python-pptx text dump + grep), not just the newest. Patch the generator JS, rebuild, re-verify zero hits.
- **After product renames, verify CLAIMS not just names.** When a product is mass-renamed across decks (Intune EPM → Idira), claims that were true for the old product silently become false — e.g. "Included in M365 E5 at no additional cost" survived the rename (Intune EPM IS in E5; Idira is paid Palo Alto software). Grep for cost/licensing/vendor claims after any rename pass, and check for orphaned structure (a "Layer 4" section that no longer exists, duplicate product columns in tables).

## References

- wdac-applocker-implementation.md — Detailed WDAC/AppLocker implementation guide with XML examples, gotchas, and deployment steps
- cyberark-epm-vs-wdac-debate.md — CyberArk EPM vs WDAC debate: governance vs threat defense, CVE track record, CyberArk's 3-layer framework for portable apps
- jamf-vs-santa-workshop-comparison.md — Jamf Protect vs Santa/Workshop comparison: EDR vs binary authorization, deployment considerations, CrowdStrike coexistence
- portable-app-governance-research.md — Research findings: Idira EPM as primary governance tool, WDAC limitations for portable apps, what enterprises actually do, other EPM vendor approaches, diplomatic framing
- idira-vs-wdac-capability-reference.md — Comprehensive capability comparison: what each tool CAN and CANNOT do, scenario winners table
- essential-eight-compliance.md — Essential Eight specifics: ISG exclusion, File Path Rules guidance, ISM control mapping, policy configuration requirements
- portable-app-discovery-mde.md — provenance-based KQL methodology for discovering portable apps at scale (15k+ devices): 9-signal scoring model, FileProfile() batching via Advanced Hunting API, MCP-confirmed dead ends, and the three-mode enrichment pipeline (Full / AH API / Offline / SingleFile); the deep playbook lives in the mde-advanced-hunting skill
- portable-app-options-triple-check-2026-08.md — Fresh 3-pass MCP research (Aug 2026): verified options menu (WDAC / AppLocker / EPM / reputation / convert-and-manage / Santa), org-practice consensus with per-claim source counts, multi-source gotchas, Firecrawl + MS Learn tooling pitfalls, key URLs
- portable-app-discovery-pipeline.md — Current working design: two-score model (Portability/Risk), DISCOVERY vs GOVERNANCE query shapes, initiator classes (Browser/Email/Archive/OfficeMacro/ScriptHost), extra risk signals (renamed binary, cmdline cradles, persistence, AI tool, non-standard ports, empty/spoofed metadata, office drops, candidate-scoped DLL sideloading), dead ends incl. packer detection, PowerShell engineering pitfalls (KQL-in-separate-file rule, parser traps, patch-tool brittleness), auth without app registration

## New Findings (July 2026 — Verified via MCP)

### Portable-App Options Triple-Check (Aug 2026 — fresh 3-pass MCP research)

Full source-verified bank: portable-app-options-triple-check-2026-08.md. Highlights:
- CyberArk article "EPM - How to Contain User-Based Applications" (community.cyberark.com, article 000050743, Apr 2026) is now tagged **Idira Endpoint Privilege Manager (EPM)** — fresh citation for the rebrand. 3-layer framework re-verified: L1 risk-reduction (restrict all user-based apps from sensitive OS components), L2 allowlist by Location (%USERPROFILE% incl. subfolders) + Publisher + Original Filename + Checksum (checksum = the matcher for UNSIGNED files, since metadata/filenames in user profiles can be altered), L3 discovery/log then default-deny. Article names Agentic AI (Claude, Cursor) as the growing driver of user-profile portable apps.
- ThreatLocker KB: Learning Mode does NOT auto-profile files in Documents/Downloads/Desktop/Users — portable apps in user dirs don't silently auto-allow. Unsigned files: combine path+process+created-by (never a single parameter). Don't permit Microsoft certificates broadly.
- Ivanti Trusted Path: path allow with optional owner-attribute restriction; dev/test churn use case.
- Santa: google/santa repo ARCHIVED (2025); maintained fork = github.com/northpolesec/santa; docs at santa.dev. Third mode beyond MONITOR/LOCKDOWN: Standalone (user approves via TouchID, auto-creates local SigningID/SHA-256 rule).
- winget portable packages (winget-cli spec #182) = convert-and-manage option for legit portable apps.
- MS recommended block-rules page moved: .../design/applications-that-can-bypass-appcontrol (old "microsoft-recommended-block-rules" URL 404s).

### ISG Retirement & Smart App Control Status (Aug 2026 — MCP-verified)

Full sourced detail: isg-retirement-and-smart-app-control-2026.md. Key facts:
- The ONLY official Microsoft retirement statement on ISG is MC1295285 (Message Center, Apr 29, 2026): the Power Platform "Microsoft Graph Security connector" is deprecated "following the deprecation of the Intelligent Security Graph service that is utilized for this connector's functionality." Replacement: Microsoft Graph Security API (v2).
- NO official notice retires the WDAC/App Control "Enabled:Intelligent Security Graph" option as of Aug 2026. MS Learn still lists it as available (feature-availability page updated Mar 2026), the App Control Wizard still ships "Signed and Reputable," Intune still shows "Trust apps with a good reputation," the troubleshooting guide still references it. Zombie-option pattern: docs unmaintained, backend service family decommissioned.
- Naming trap — three different "ISGs": (1) marketing concept = telemetry data plane powering Defender products (alive, re-branded "Microsoft Defender Intelligent Security Graph"); (2) ISG service behind the Power Platform connector (RETIRED Apr 29, 2026); (3) reputation lookup used by the WDAC ISG option + Smart App Control (same family, still documented, no official status statement).
- The reputation DATA persists in Defender: SmartScreen AppRep docs updated May 2026; MDE FileProfile() prevalence continues; MDTI portal retired Aug 1, 2026 with intelligence folded into the Defender portal; MDE/XDR Advanced Hunting APIs retire Feb 1, 2027 but consolidate into Graph Security API v2 (MC1220762).
- Microsoft's documented alternative to ISG in App Control = managed installer + signed catalog files + explicit rules (lightly-managed devices page). No new reputation feature announced; ISG remains the only reputation mechanism in the feature matrix.
- Practical stance for proposals: never claim "ISG is dead" (live docs contradict you). Say "reputation service deprecated Apr 2026; App Control docs unmaintained; no replacement announced; plan for explicit controls." If ISG goes into a starter policy, pilot 50 devices 7-10 days and watch CodeIntegrity events 3076/3077 for whether reputation-based allows actually fire.
- Smart App Control updates (Apr 2026, KB5083769 / Win11 25H2 / Windows Security app v1000.29554+): re-enabling after turning off no longer requires a reset. Still consumer-only: auto-disables on enterprise-managed devices, no management surface. When enabled, SAC disables SmartScreen AppRep and drops Defender AV into "hybrid" mode (less-active real-time protection) — a real trade-off if anyone proposes SAC fleet-wide. SAC blocks MotW'd dangerous file types from ShellExecute with no override; ECC code signing unsupported in the CI codepath (being addressed).

### Triple-Check / Fresh-Research Protocol (user preference, Aug 2026)
When the user asks for a "triple check" or says "disregard previous conversations / use mcp": run 3 independent passes (broad landscape search -> community/vendor search+scrape -> primary-source verification), report per-claim source counts, disclose gaps honestly (e.g. "Reddit snippet-level only"), and use MCP search/scrape (exa/firecrawl) rather than plain web tools. Treat loaded-skill conclusions as hypotheses to re-verify — do NOT parrot prior-session findings; the exercise is independent re-verification.
Firecrawl pitfalls (verified): refuses Reddit ("we do not support this site") — use firecrawl_search snippets; formats:["query"] LLM extraction is thin on big pages — use formats:["markdown"]; MS Learn URLs drift — re-search on 404.
- Retirement/deprecation verification (Aug 2026): search Message Center archives (mc.merill.net, tophhie.cloud, cloudscout.one) by MC ID — they preserve full MC text; cross-check the feature-availability page; look for post-cutoff functional reports; if ambiguity remains, recommend a pilot test instead of asserting either way.
- exa advanced search with includeDomains=[learn.microsoft.com] can return enormous irrelevant API-reference pages (multi-hundred-K truncated dumps) — cap numResults/textMaxCharacters, and prefer firecrawl_search with includeDomains for domain-restricted lookups.

### Santa (macOS) Updates
- Sandbox profiles (2026.5): NEW — ringfencing for macOS. Attach seatbelt profile to a rule. Target by Team ID, SigningID, or hash.
- **Limitations:** Does NOT block scripts (shell/Python/Ruby bypass Santa). Does NOT protect against dlopen/DYLD_INSERT_LIBRARIES (SIP protects when enabled). No driver control.
- Team ID: ZMCG7MLDV9. 4 MDM profiles needed: System Extension, TCC, Notifications, Santa Config.
- **CrowdStrike coexistence:** CrowdStrike Falcon for macOS uses the same Endpoint Security Framework (ESF). Can coexist with Santa. Santa = binary authorization (pre-execution), CrowdStrike = EDR (behavioral detection). Both subscribe to AUTH_EXEC events.
- **Transitive allowlisting:** Mark compilers (Xcode) with ALLOWLIST_COMPILER. Build output auto-trusted for 6 months. Machine-local only.
- **Deployment:** Via Jamf as Installer Package (.pkg). Jamf supports "Audit and Enforce" mode. Packages are signed and notarized. Can also use Munki, Fleet (GitOps), or manual install.

### Workshop by North Pole Security (Enterprise Santa Management)
Santa alone = manual rule management per device. Workshop = enterprise management platform built by the same team (Santa's original creators at Google).

**Why Workshop matters:**
- Centralized rule management with sync protocol — push policy changes to all endpoints in seconds
- Approval workflows: self-service, designated approvers, social voting — when Lockdown blocks something, users get it approved in minutes, not days
- Risk engine: VirusTotal, ReversingLabs integration — auto-screens unknown binaries before human review
- Package rules: Homebrew, npm, Cargo, GitHub Releases, VS Code extensions, Terraform — auto-allowlist developer tools
- File access authorization — control which processes can read/write sensitive files (SSH keys, cookies, keychains)
- USB/SD blocking — prevent data exfiltration via removable media
- Telemetry with SQL queries + management zones + audit trails
- SOC 2 compliant. Cloud-hosted or self-hosted.
- Private sync protocol (faster than open-source sync servers)
- $4M seed from Andreessen Horowitz (2025)

**Alternatives to Workshop (open-source sync servers):**
- Moroz: simple golang server, hardcoded rules
- Rudolph: AWS-based serverless (API GW + DynamoDB + Lambda)
- Zentral: event hub with Santa management
- Fleet: GitOps-native device management with Santa support

### CyberArk EPM macOS Updates (v26.5)
- **Script validation via Team ID and Signing ID:** Administrators can target macOS scripts in policies using Apple Team IDs and Signing IDs. More precise control by verifying developer identity and code signature.
- **Supported interpreters:** /bin/bash, /bin/csh, /bin/ksh, /bin/sh, /bin/tcsh, /bin/zsh
- **Scripts enforced when executed directly:** `./myscript.sh` or `bash ./myscript.sh` (without interpreter parameters)
- **Homebrew issue:** Homebrew installation fails with EPM due to admin rights assumptions. Solution: use customized installation script or exclude Homebrew paths.
- **SIP monitoring:** "Only elevate macOS applications if notarized by Apple or protected by SIP. Set Monitor SIP files in Agent Configuration to On."
- **Intune integration:** "Exclude service accounts from access restrictions" setting must be DISABLED for Intune "Install as system" to work with EPM. Otherwise system-level processes bypass EPM policy evaluation.

## Common Deployment Anti-Patterns (Verified July 2026)

These are the most common mistakes teams make when designing application control for portable apps. They were independently verified in a July 2026 re-review.

### Anti-Pattern 1: Using WDAC FilePath Rules for User-Writable Paths
**The mistake:** Creating WDAC FilePath rules for %USERPROFILE%\Downloads, %TEMP%, %APPDATA%, or Desktop.
**Why it's wrong:** WDAC refuses to create FilePath rules for user-writable directories — by design. The runtime user-writeability check blocks them. The only workaround is Option 18 (Disabled:Runtime FilePath Rule Protection), which disables the guardrail designed to prevent exactly this attack.
**The fix:** Use AppLocker for per-user path-based deny (AppLocker doesn't have the admin-write-only constraint). Use Idira EPM for location-based application governance with publisher + checksum enforcement.

### Anti-Pattern 2: WDAC as Primary Portable App Governance Tool
**The mistake:** Building a WDAC-centric architecture with WDAC as Layer 1-2 for portable app blocking.
**Why it's wrong:** Less than 15% of enterprises enforce WDAC in block mode. Most projects fail or roll back within 24 hours. WDAC was designed for kernel enforcement and compliance — not portable app governance. Every major EPM vendor uses provenance-based control for this problem.
**The fix:** Idira EPM as Layer 1 (primary). AppLocker for per-user path rules (Layer 2). WDAC scoped to kernel drivers + PowerShell CLM only (Layer 3).

### Anti-Pattern 3: Treating Managed Installer as a Clean Solution
**The mistake:** Presenting managed installer as a "game-changer" without disclosing gotchas.
**Why it's wrong:** Six critical failure modes:
1. Backlog problem — apps installed before MI won't get EA tags
2. Self-updating apps (Chrome, VS Code, Teams) break MI — updates happen outside MI channel
3. IME -PowerShell command injection allowed regular users to write MI-trusted files (CVE-2021-41363, fixed in newer versions)
4. File copy strips origin claims (Explorer loses them; robocopy preserves)
5. Any admin can designate PowerShell as managed installer via registry (BSides Umeå 2026)
6. Process tree propagation — child processes of MI-trusted installers also get tagged
**The fix:** Managed installer is a helper, not a solution. Pair it with Idira's Trusted Sources model. Audit MI-tagged files regularly. Never rely on MI alone for security-critical enforcement.

### Anti-Pattern 4: Claiming "WDAC Cannot Be Bypassed by Admin"
**The mistake:** Stating WDAC provides kernel-level enforcement that "even local admins can't bypass" as an absolute.
**Why it's wrong:** Documented bypasses exist:
- CVE-2025-26678: WDAC security feature bypass (CVSS 8.4, no privileges needed, no user interaction)
- CVE-2024-43645: WDAC security feature bypass (CVSS 7.8)
- CVE-2026-25166: imgmgr.exe deserialization bypass (not on recommended block list as of July 2026)
- Managed installer abuse: admin can deploy malicious AppLocker policy via registry
- EDR disabling via crafted WDAC policy (seen in the wild)
**The fix:** Qualify the claim: WDAC is the strongest option available, but "can't be bypassed" is only true with signed policies + HVCI. Unsigned policies are trivially bypassable. Red teams measure bypass in single-digit minutes for unsigned deployments.

## Recommended Architecture (July 2026 — Verified via MCP Research)

**Idira EPM is the PRIMARY application governance tool. WDAC+AppLocker is minimal scope only.**

### Why Idira for Governance (Not WDAC)

Research across enterprise practice revealed:
- **WDAC can't handle user-writable paths** (Downloads, %LOCALAPPDATA%) — by design. Portable apps live there. WDAC refuses to create FilePath rules for user-writable directories.
- **Less than 15% of enterprises have WDAC enforced in block mode** (Decryption Digest, 2026). Most never complete deployment.
- **WDAC deployments take 6-9 months** and often fail. Common failure: deploy enforce mode without adequate baseline data.
- **Every major EPM tool uses provenance-based control** — CyberArk (Trusted Sources), Ivanti (Trusted Ownership), ThreatLocker (Learning Mode), BeyondTrust (QuickStart). The industry standard is EPM for governance, not WDAC.
- **CyberArk EPM has a dedicated 3-layer framework** specifically for portable apps (from CyberArk community article "EPM - How to Contain User-Based Applications"):
  - Layer 1: Risk-reduction controls — restrict all user-based apps from sensitive OS components
  - Layer 2: Allowlist for approved user-based apps — Location + Publisher + Original Filename + Checksum
  - Layer 3: Discovery and default-deny — discover first, then enforce

### The Right Tool for Each Job

| Tool | Scope | Why |
|---|---|---|
| **Idira EPM** | All application governance | Portable apps, privilege management, ringfencing, cross-platform, self-service elevation, per-user policies |
| **WDAC+AppLocker** | Kernel drivers + PowerShell CLM only | Idira can't control kernel drivers or enforce CLM. Minimal scope — don't try to use for application governance. |
| **Santa + Workshop** | macOS binary authorization | Pre-execution blocking via ES_AUTH_EXEC that Idira can't do. Sandbox profiles (2026.5) for ringfencing. |

### What Idira Can't Do (And What Fills the Gap)

| Gap | Why Idira Can't | Solution |
|---|---|---|
| Kernel driver control | Idira operates in user mode | WDAC — minimal policy for signed kernel drivers only |
| PowerShell CLM | Idira can restrict but not enforce CLM | WDAC — CLM policy via managed installer |
| Pre-execution blocking (macOS) | Idira's macOS agent doesn't intercept at ES_AUTH_EXEC level | Santa — ES_AUTH_EXEC kernel extension |
| Binary reputation (macOS) | Idira uses cloud reputation for Windows only | Santa + Workshop — local rules + sync server |

### What Other EPM Vendors Do for Portable Apps

All major EPM vendors use provenance-based (trusted ownership) control:
- **CyberArk EPM**: Trusted Sources + Inherited Trust (3-layer framework)
- **Ivanti**: Trusted Ownership model — files placed by SYSTEM/admin are allowed, user-introduced content denied by default
- **ThreatLocker**: Learning Mode + Ringfencing™ — hash-based detection, controls file/registry/network access
- **BeyondTrust**: QuickStart templates + Trusted Ownership — pre-configured policies for different flexibility levels

### Diplomatic Framing for the Shift

When presenting the move from "WDAC for everything" to "Idira for governance":
- **NEVER say** "WDAC can't handle portable apps" or "we were wrong"
- **ALWAYS say** "WDAC was designed for kernel enforcement and compliance — not portable app governance. Our existing CyberArk EPM has a purpose-built framework for this exact problem. This is the right tool for the right job."
- Frame as evolution, not correction: "Initial guidance followed Microsoft's official recommendation. Deeper research into enterprise practice revealed EPM tools are the standard for portable app governance."

### Single-Vendor Risk Mitigation

- WDAC is built into the OS — doesn't depend on a vendor
- If CyberArk has an outage/vulnerability, WDAC still enforces kernel drivers
- WDAC is free (included in Windows), Idira is paid
- Use WDAC for the security-critical kernel layer, Idira for the governance layer

## Why "Everyone" Recommends WDAC + AppLocker (Even Though Idira Is Better for Portable Apps)

When users push back with "why does everything recommend WDAC?", the answer has four distinct layers — often conflated. This section equips you to explain it clearly.

### 1. Microsoft Controls the Narrative
Since 2022, Microsoft has been explicit: WDAC is the strategic direction, AppLocker is maintenance mode. This cascades to compliance frameworks, MSPs, consultants. EPM vendors recommend their own tools but nobody hears them over Microsoft's megaphone. Their docs say: *"Generally, customers who are able to implement application control using App Control, rather than AppLocker, should do so."*

### 2. Essential Eight Mandates WDAC at ML2 (For Specific Reasons)
ASD explicitly says: ML1 = AppLocker OK, ML2/ML3 = WDAC only. WHY: driver control, server coverage, recommended blocklist, all-locations enforcement. These are about THREAT DEFENSE, not portable app governance. The ASD says "implement application control" — they don't say HOW. Microsoft's own Essential Eight guidance says: *"File Path Rules are not recommended for ISM-1870 due to the user having file system permission within user's profile and temporary folders."*

### 3. "Application Control" = "WDAC" in Industry Shorthand
EPM vendors market as "privilege management" not "application control." Idira, Ivanti, ThreatLocker all DO application control — but the term defaults to WDAC in security literature. Branding problem, not capability gap.

### 4. "Free" Is Seductive (Hidden Costs Are Invisible)
WDAC is included in Windows. No procurement, no vendor. But: 6-9 months staff time, SIEM setup, failed rollouts, helpdesk burden. Idira is paid but deploys in 2-4 weeks. TCO comparison doesn't happen because WDAC's costs are indirect.

**Key insight:** Nobody says "WDAC is best for portable app governance." The ASD says "implement application control" — Microsoft says "use WDAC for it." Even Microsoft's own Essential Eight guidance says File Path Rules are NOT recommended for user profiles. The leap from "WDAC is the right tool for kernel enforcement" to "WDAC is the right tool for portable app governance" is the error most teams make.

## Verified CVEs (MCP-Verified, July 2026)

### WDAC Bypass CVEs
| CVE | CVSS | Description | Status |
|---|---|---|---|
| CVE-2025-26678 | **8.4** (HIGH) — AV:L/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H | WDAC security feature bypass. No privileges needed, no user interaction. Fixed April 2025. | Patched |
| CVE-2024-43645 | **7.8** (NVD) / 6.7 (Microsoft) — PR:L vs PR:H disagreement | WDAC security feature bypass. Different CVSS scores from NVD vs Microsoft. Fixed November 2024. | Patched |
| CVE-2026-25166 | N/A | imgmgr.exe (Windows ADK) insecure deserialization bypasses WDAC. Discovered April 2026 by dotSec. **Not on Microsoft's recommended block list as of July 2026.** Affects all Windows 10/11 and Server builds. | **Unpatched — manually block** |
| CVE-2025-33069 | **5.1** (MEDIUM) — AV:L/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N | Improper cryptographic signature verification in WDAC. Fixed June 2025. | Patched |

### Idira EPM CVEs
| Bulletin | Severity | Description |
|---|---|---|
| CA26-24 | HIGH | EPM SaaS Windows Agents, all versions prior to 26.6 |
| CA26-25 | HIGH | EPM SaaS Windows Agents, all versions prior to 26.6 |

## Idira EPM Known Issues (Verified via MCP, July 2026)

**Critical — OS Update Breakage:**
- Win11 22H2 + KB5025224: "Severe performance issues, including failing to start and function properly." EPM service wouldn't start. Required emergency agent upgrade.
- Win10 KB5023773/KB5025221: "The EPM service will not be able to start, meaning that agents cannot execute/enforce policies or rotate credentials. All agent functionality will be affected."

**High — Agent Conflicts:**
- Digital Guardian: "Performance problems with Digital Guardian and EPM's Anti-Tampering Protection setting — symptoms include: Inability to save downloads, System slowness when launching applications"
- BitDefender and Microsoft Defender conflicts also documented
- Chromium-based browser performance issues: "Opening or switching between multiple tabs simultaneously could cause the browser to stop responding." Fixed in agent v26.2.1.

**Known Issue Tracker:** 30+ known issues including: agent disconnection after upgrade, proxy config loss after restart, endpoint status inconsistent in console, trust policy breakage after agent upgrade, memory/resource problems cause policy loss, policy migration failures.

**Agent DLL Interference:** vf_inj.dll (CyberArk injection DLL at `C:\Program Files\CyberArk\Endpoint Privilege Manager\Agent\x64\vf_inj.dll`) has caused crashes in other applications (Windows Update check, etc.). Fixed in newer agent versions.

**ARM Limitations:** No elevation with restrictions on ARM-32 emulated processes. Video audit recording on ARM causes system unresponsiveness.

### Essential Eight Compliance Specifics

- **ISG explicitly excluded from Essential Eight:** Microsoft's Essential Eight guidance states: *"Reputation-Based Intelligence for Application Control does not meet the Essential Eight Application Control due to the requirement 'Organization-approved set' (ISM 1657) and 'Application control rulesets are validated on an annual or more frequent basis' (ISM 1582)."* ISG must be set to Disabled for ML2/ML3 compliance.
- **File Path Rules not recommended:** *"File Path Rules are not recommended for ISM-1870 due to the user having file system permission within user's profile and temporary folders."* Microsoft recommends File Publisher Rules or File Hashes instead.
- **ML2 requires WDAC specifically** for: driver control, recommended application blocklist, server coverage, all-locations enforcement, centralized event logging.

## Code Signing for Internal Tools (Options & Cost, verified Aug 2026)

When the discussion turns to "should we sign our internal tools" (proposal, portable-apps
session, or WDAC publisher-rule enablement), the procurement facts live in
code-signing-internal-tools.md. Headlines:
- **Azure Artifact Signing** (renamed from Trusted Signing): Basic $9.99/mo / 5,000
  signatures, $0.005 per extra sig; Premium $99.99/mo / 100,000. Public + private trust
  profiles, keys never leave the service. No free/trial/sponsored subscriptions. Not pro-rated.
- **ADCS internal CA** = private trust only, SmartScreen never recognizes it, PKI program
  to operate. **OV/EV public cert** = SmartScreen-friendly but HSM + manual renewal + EV cost.
- Pipeline: Artifact Signing account → CI signing step (signtool + timestamp) →
  Set-AuthenticodeSignature for PowerShell → Intune/winget ship → one WDAC publisher rule.
- Portable-apps angle: signing org portables converts hash exceptions → publisher rules;
  scripts signed = CLM Full Language Mode + script rules without weakening policy.
- Unsigned-tool frictions (SmartScreen, hash churn, MDE reputation, MOTW, tamper
  detection, audit trail) and proposal framing that landed (ask = $120/yr + 1 CI step +
  1 pilot; never invent org-specific metric claims) are in the same reference.

## Compliance Framework Map for Signed Code / App Control (Verified Aug 2026)

Which frameworks actually require internal tools to be signed/certed — with exact clauses:
- **OSFI B-13 §3.2.4 "Cyber security controls are layered"** (Canadian FRFIs incl. insurers; effective Jan 1 2024; risk-based not prescriptive): "Leverage a combination of allow/deny lists, including file integrity checks (e.g., file hash/signature) and indicators of compromise, in addition to advanced behaviour-based protection capabilities that are continuously updated." Examiners ask how you control what runs + verify integrity — hash/signature checks named explicitly. Adjacent: B-13 CSSA self-assessment tool (XLSX, Nov 2025, aligned to B-13); preventive-over-detective posture throughout. Related: B-10 (third party), E-4 (operational resilience).
- **NIST SP 800-53 CM-14 Signed Components** (R5.2.0): prevent installation of org-defined software/firmware components unless digitally signed with a cert recognized/approved by the org. Org scopes which components. Related: SC-12/SC-13, SI-7. FedRAMP-relevant; CCCS ITSG-33 mirrors it for Canadian federal.
- **CIS Controls v8**: 2.5 Allowlist Authorized Software (technical controls, bi-annual reassessment), 2.7 Allowlist Authorized Scripts (digital signatures + version control; block unauthorized scripts; bi-annual). IG3.
- **ISO 27001:2022 A.8.28 Secure coding**: verification before release; signing is the standard integrity/non-repudiation mechanism auditors expect in the internal SDLC pipeline.
- **PCI DSS 4.0 §6.4.3 + 11.6.1** (only if card payments): payment-page scripts must be authorized + integrity-checked + inventoried; digital signatures listed as acceptable integrity mechanism; 11.6.1 = tamper detection. Effective Mar 31 2025.
- **FFIEC IT Handbook** (US banking): Development booklet — secure coding + "security certification for completed systems and component-related code"; no explicit signing mandate.
- **Essential Eight ISM-1870**: app control rulesets validated annually; publisher/hash rules preferred, path rules NOT recommended for user profiles.
- No Canadian insurance regulation literally mandates "all internal tools signed" — B-13 is risk-based; the signing requirement is operationalized via CM-14 (FedRAMP/US exposure) and CIS 2.5/2.7. Implementing Idira + WDAC IS the evidence for these controls.

## Parent→Child Trust Semantics (Can a Signed Parent Approve Its Children?) (Verified Aug 2026)

**Answer: no blanket inheritance in any tool — every binary is evaluated individually.** Three mechanisms approximate it, with very different semantics:

1. **Cert-level (not parent-level) publisher rules** — the correct "signed parent covers the rest" pattern: sign ALL internal tools (launcher + payload + scripts) with one org cert → ONE publisher rule (Idira Publisher's signature / WDAC FilePublisher / AppLocker Publisher) covers the whole family, survives updates. The only safe, auditable, update-proof option.
2. **File-origin trust (parent WRITES → child trusted):**
   - **Idira: Trusted Sources + Inherited Trust** (docs.cyberark.com key concepts — VERIFIED): trust propagates from trusted source (Software distributor [SCCM/ePO/Intune], Network share, Publisher's signature, Installation package, Software updater, User, URL, Product name) to apps it installs "even if these applications bear a different digital signature"; RETROACTIVE — source info stored in file EA ("Store file info in extended attribute = On" in agent config), follows the file through moves/copies. Closest thing to the requested behavior. Gotchas: (a) applies to files the trusted source WRITES (installs/extracts), not processes it merely spawns; (b) official docs: URL trust type requires a publisher; community-reported (snippet-level) that trusted-source policies now require a publisher signature generally; (c) user-mode agent down = no enforcement; (d) compromised trusted writer = inherited trust laundering (IME CVE-2021-41363 class); (e) retroactive = pre-existing files from that source are trusted, so scope trust policies tightly.
   - **WDAC Managed Installer (Option 13)** — MS Learn technical reference VERIFIED EA semantics: $KERNEL.SMARTLOCKER.ORIGINCLAIM, second ULONG 00=MI / 01=ISG; third ULONG 00 = directly written by MI process = ALLOWED; **02 = "child of child" (file created by something MI installed, AFTER MI finished) = NOT allowed** without another rule. One-hop at write-time only, not retroactive; copy strips EAs (robocopy preserves); requires AppLocker plumbing (appidsvc + AppLockerFltr running, MANAGEDINSTALLER + EXE/DLL RuleCollections, RuleCollectionExtensions); admin can designate any MI. Runtime-generated binaries (e.g. scripts compiling exes at run time) are NOT covered — the exact gap for portable/script-launcher patterns.
   - **AppLocker: ZERO inheritance** — per-file matching only (publisher/path/hash). Its roles: per-user rules, MI plumbing for WDAC, cert-level publisher rules.
3. **Reputation (ISG/Smart App Control)** — ISG-trusted installers' file writes inherit reputation (same EA, second ULONG 01). ISG service retired Apr 2026 (MC1295285); docs unmaintained; do not build on it.

**Why the naive ask is wrong:** "signed parent approves everything it calls" is exactly the chain attackers exploit (LOLBins, msiexec/rundll32 parents, IME injection). All three tools evaluate children independently on purpose. Config guidance for portable/user-context apps: sign everything → one publisher rule; unsigned children that only exist after a trusted parent writes them → Idira Trusted Source + Inherited Trust; WDAC stays kernel+CLM (add MI only for native installs, knowing the EA=02 gap); scripts (e.g. run-ah.ps1-style one-shots) → sign with org cert for CLM Full Language Mode + Idira script publisher rule.

**"Sign everything" receipts (direct citations for why ALL binaries must be signed, verified Aug 2026):**
- Microsoft Learn "Use code signing for added control and protection with App Control": "Wherever possible, you should require all app binaries and scripts are code signed as part of your app acceptance criteria. And, you should ensure that internal line-of-business (LOB) app developers have access to code signing certificates controlled by your organization." Catalog files = the fallback for unsigned LOB apps (add a signature without repackaging; hash-based, must redeploy on update). https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/deployment/use-code-signing-for-better-control-and-protection
- NIST SSDF (SP 800-218) PS.2 "Provide a Mechanism for Verifying Software Release Integrity", PS.2.1 Example 2: "Use an established certificate authority for code signing so that consumers' operating systems or other tools and services can confirm the validity of signatures before use." https://csrc.nist.gov/pubs/sp/800/218/final
- Microsoft "Applications that can bypass App Control" — the signed-parent problem made concrete: Microsoft maintains a blocklist of VALID signed apps (addinprocess32.exe, lxrun.exe, msbuild.dll, windbg.exe...) attackers use to bypass allow policies; every binary must be evaluated, not just the parent. https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/design/applications-that-can-bypass-appcontrol



When comparing macOS application control options:

**Jamf Protect:**
- Apple-native EDR built on Endpoint Security Framework
- Application controls: block by hash, Team ID, Signing ID (default-allow, not default-deny)
- Custom Prevent Lists: up to 100K entries (blocklist, not allowlist)
- Behavioral detection: JQL analytic rules mapped to MITRE ATT&CK
- Jamf Pro integration: unified MDM + security console
- Limitation: NOT binary authorization. Default-allow model. Unknown binaries still run.

**Santa + Workshop (North Pole Security):**
- Purpose-built binary authorization. Default-deny in Lockdown mode.
- 5 rule types: CDHash → Binary → Signing ID → Certificate → Team ID
- Transitive allowlisting: approved compilers auto-trust output for 6 months
- Sandbox profiles (2026.5): ringfencing for macOS
- Approval workflows: self-service, designated approvers, social voting
- Risk engine: VirusTotal, ReversingLabs auto-screen unknown binaries
- Limitation: NOT EDR. No behavioral detection, no threat hunting.

**Recommendation:** Santa/Workshop for binary authorization (prevention) + Jamf Protect or CrowdStrike for EDR (detection). They complement each other — Santa blocks what shouldn't run, EDR catches what slips through.

## WDAC Gotchas (Verified via MCP)

- Signed policies + HVCI = reboot required (Win11 <24H2)
- 32 policy limit (pre-April 2024 = bluescreen with bugcheck 0x3b)
- PowerShell CLM blocks COM/Win32 API/Dynamic loading
- Managed installer backlog: apps installed BEFORE enabling MI won't get EAs
- ISG trust laundering: ISG-trusted apps can pass trust to arbitrary executables
- ISG service retired Apr 2026 (MC1295285); App Control ISG option = zombie (docs lag, no replacement announced) — see New Findings + isg-retirement-and-smart-app-control-2026.md
- AppLocker: doesn't enforce on services by default — needs RuleCollectionExtensions XML
- WDAC bypasses: IME -PowerShell command injection, imgmgr.exe deserialization (CVE-2026-25166), EDR disabling via crafted policy. MITIGATION: signed policies + HVCI.
- MSI files always detected as user-writable on Win10 and Server 2022 and earlier
- Option 19 (Dynamic Code Security) always enforced in audit mode
- CA expiration (July 2025): 15-year Microsoft issuing CAs expiring. Auto-inference logic handles new CAs.
- CVE-2025-33069: Improper cryptographic signature verification. CVSS 5.1. Fixed June 2025.
- CVE-2025-59033: Driver blocklist entries with FileAttribRef qualifier not blocked without HVCI.


## Reference: code-signing-internal-tools.md

# Code Signing for Internal Tools — Options, Cost, Pipeline (verified Aug 2026)

Companion to the SKILL.md sections "Compliance Framework Map for Signed Code" and
"Parent→Child Trust Semantics". This file covers the PROCUREMENT side: how to get a
signing identity for internal/portable tools, what it costs, and how the pipeline
fits existing CI. Built while producing an org proposal deck ("Sign what we ship").

## Why sign internal tools (the six frictions unsigned code causes)

1. **SmartScreen friction** — first run from download/share throws "unknown publisher".
2. **WDAC/AppLocker hash churn** — unsigned code can only be allowed by file hash;
   every rebuild forces a policy update. Publisher rules REQUIRE signed files
   (MS Learn: "publisher conditions can be made only for files that are digitally
   signed"). One publisher rule covers all future versions of the same cert.
3. **MDE/Defender suspicion** — unsigned binary = no reputation; each release is a
   fresh unknown that can trigger detections and burn IR time.
4. **Mark-of-the-Web noise** — files pulled from portals/Teams/shares flagged on
   arrival even when org-built.
5. **No tamper detection** — nothing proves a binary is the org's build.
6. **Weak audit trail** — no identity in the event chain for IR.

MS Learn stance ("Use code signing for added control and protection with App
Control"): require all app binaries AND scripts code-signed as acceptance criteria;
LOB devs get org-controlled signing certs; catalog files are the fallback for
unsigned LOB apps. See SKILL.md "Sign everything" receipts for URLs.

## The three options (decision table)

| Option | Trust surface | SmartScreen | Operational burden | Cost |
|---|---|---|---|---|
| Internal CA (ADCS) | Private trust only | Never recognizes it | Runs the PKI: issuance, revocation, compromise response | Free $, expensive as a program |
| Public OV/EV cert | Public | Yes | Keys need HSM protection, manual renewal, EV is expensive | Real money |
| **Azure Artifact Signing** (formerly Trusted Signing) | Public + private profiles | Yes | Microsoft-managed; keys never leave the service; CI integration | $9.99/mo Basic |

**Azure Artifact Signing facts (verified Aug 2026, Microsoft pricing page):**
- Renamed from "Trusted Signing" (pricing page says pricing unchanged from Trusted Signing).
- Basic: **$9.99/month**, 5,000 signatures included, **$0.005 per signature** after.
- Premium: **$99.99/month**, 100,000 signatures, $0.005 per signature after.
- Basic = 1 certificate profile of each type; Premium = 10 of each type.
- Public trust + Private trust signing both included.
- **No free/trial/sponsored Azure subscriptions** — needs paid subscription (pay-as-you-go or EA).
- Not pro-rated: full SKU amount billed regardless of when account is created in the month.
- Signing quota is per certificate profile, not aggregated across profiles.
- Recommendation for internal tooling: Artifact Signing Basic; keep ADCS only for
  pre-existing PKI needs (ADCS can't make SmartScreen happy, ever).

## Pipeline (mostly plumbing the org already runs)

1. Stand up Artifact Signing account + certificate profiles (public/private trust).
2. Add signing step to CI (Azure DevOps / GitHub Actions task; `signtool sign`
   with `/tr` timestamp — always timestamp, signatures must outlive the cert).
3. Sign everything: binaries with signtool, PowerShell scripts with
   `Set-AuthenticodeSignature` (script signing so execution policy / WDAC script
   rules can trust org scripts without weakening checks for everything else).
4. Ship as usual (Intune / winget); signature rides along silently.
5. Trust once: add WDAC publisher rule for the org cert (PcaCertificate/FilePublisher
   level) — policy work per release drops to zero.

Only genuinely new piece is step 1; keys never touch a dev machine (managed service).

## Portable-apps tie-in (for the portable/governance discussion)

- Org-built portables: move from hash exceptions → one publisher rule covering all
  future versions (kills the per-update policy churn from the SKILL.md hash-rule notes).
- Third-party portables: unchanged, stay on the existing allowlist path; signing
  org tools shrinks the exceptions list to only what the org didn't build.
- Scripts (e.g. run-ah.ps1-style one-shots): sign with org cert → CLM Full Language
  Mode + script publisher rules work without weakening policy (ties to SKILL.md
  Parent→Child section's config guidance).

## Proposal framing that landed (deck copy, Aug 2026)

- "Our own tools are strangers in our own environment" — unsigned binaries have no
  identity for SmartScreen/WDAC/Defender.
- "Signing is the trust mechanism our policies already assume" — publisher rules
  only exist for signed code; every signed portable tool is one less exception to
  maintain, explain, and audit.
- Ask shape: $120/yr (Basic), 1 CI step, 1 pilot (portable catalog → swap hash
  exceptions for publisher rules, measure over a quarter).
- Don't invent org-specific metrics ("75% fewer alerts") — the honest framing is
  platform behavior, not measured org numbers; offer to pull MDE data for real counts.


## Reference: cyberark-epm-vs-wdac-debate.md

# CyberArk EPM vs WDAC — The Governance vs Threat Defense Debate

## The Core Distinction

**Governance perspective (controlling what users run):**
- Idira can do everything WDAC does for portable/user-context apps
- Idira has MORE features: per-user policies, ringfencing, cross-platform, risk engine, self-service elevation

**Threat defense perspective (defending against sophisticated attackers):**
- WDAC is kernel-level enforcement (ci.dll), Idira is user-mode agent
- WDAC with signed policies + HVCI survives SYSTEM-level attackers

## CyberArk's Own 3-Layer Framework for Portable Apps

From CyberArk community article "EPM - How to Contain User-Based Applications":

**Layer 1 — Risk-Reduction Controls**
- Restricts ALL user-based applications from invoking sensitive OS components
- Targets components commonly abused by attackers or leveraged by Agentic AI
- Establishes baseline reduction in privilege exposure

**Layer 2 — Allowlist for Approved User-Based Apps**
- Introduce an allowlist for sanctioned user-based applications
- Use Location (%USERPROFILE%) + Publisher (if signed) + Original Filename + Checksum (if unsigned)
- This layer is a placeholder for ongoing discovery

**Layer 3 — Discovery and Default-Deny**
- One policy to discover and log user-based applications
- A second, higher-priority policy that enforces default-deny
- When enabled, any unapproved or unknown user-based application is blocked and logged

**CyberArk's own words:**
> "User-Based Apps are Installer based or portable programs that users can deploy to their profiles without administrative approval. These applications reside in directories where users have full control (e.g., %USERPROFILE% on Windows). While some of these apps are legitimate, they present three primary challenges: Lack of Oversight, Strategic Misalignment, Resource Constraints."

> "These portable-apps are growing in popularity especially with the proliferation of Agentic AI. AI solutions such as Claude, Cursor, and many others all can be installed within a user profile and be utilized for privilege escalation via relatively trivial mechanisms."

## Head-to-Head Debate Results (July 2026)

### WDAC Advocate's Strongest Attacks on Idira

1. **Agent dependency** — If Idira agent crashes, all protection ceases. WDAC has no agent to crash.
2. **Mandatory SaaS** — Idira EOL'd on-prem in 2023. Forces cloud dependency, data sovereignty concerns, vendor lock-in.
3. **Performance impact** — CyberArk's own docs acknowledge slowdowns, especially for developers. WDAC only checks at binary load time.
4. **OS update resilience** — Win11 22H2 completely broke Idira. WDAC never breaks on Windows updates.
5. **Per-user rules** — AppLocker already does this. WDAC+AppLocker gives both kernel enforcement AND per-user granularity.
6. **"Ringfencing" achievable another way** — WDAC's Constrained Language Mode, script enforcement, Windows Sandbox, AppContainer achieve similar goals natively.
7. **"Cross-platform not relevant"** — If primary concern is Windows endpoints, cross-platform is irrelevant. Apple's Gatekeeper + MDM handles macOS. SELinux/AppArmor handle Linux.
8. **"JIT elevation achievable with Intune EPM + LAPS"** — Microsoft's own JIT elevation is available without third-party agent.
9. **"ISG does reputation"** — WDAC's ISG provides real-time cloud-based reputation scoring using Microsoft's telemetry from billions of endpoints.
10. **Agent attack surface** — 5+ CVEs in 2025-2026 alone. The security tool itself is a recurring attack surface.
11. **Anti-tamper conflicts** — Idira's anti-tampering causes conflicts with Digital Guardian, BitDefender, Microsoft Defender.
12. **Known bugs** — UAC conflicts, agent disconnection, Intune integration failures, performance issues with Chromium browsers, Win11 22H2 breakage.

### Idira Advocate's Strongest Attacks on WDAC

1. **Operational complexity** — 6-9 month deployments that often fail. Most organizations never complete audit→enforce transition.
2. **Kernel enforcement overstated** — Requires signed policy + HVCI + internal PKI. Most orgs deploy unsigned policies with zero tamper resistance.
3. **"Free" is misleading** — Intune costs ~$30/user/month, SIEM costs, 6-9 months of specialist staff time. TCO favors EPM.
4. **Real-world failures** — Black screen catastrophes from AppLocker CSP, 10% failure rates, WDAC blocking Visual Studio/Docker/SSMS even through Managed Installer.
5. **LOLBin exploitation is trivial** — WDAC allows all Microsoft-signed binaries by default. Attackers use msbuild.exe, regsvr32.exe, etc. to bypass.
6. **No post-execution control** — WDAC controls what runs but not what it does after running. No ringfencing.
7. **DLL collection commonly left unconfigured** — Many WDAC deployments miss DLL enforcement, leaving a gap.
8. **Red teams measure bypass in single-digit minutes** — Unsigned policies are trivially bypassable.
9. **No elevation workflow** — WDAC has no self-service elevation. Users contact helpdesk for every exception.
10. **No cross-platform** — Windows only. Large enterprises have Mac fleets.
11. **No identity awareness** — WDAC doesn't track who is running what. Can't detect insider threats.
12. **No threat intelligence** — ISG is heuristic, not comparable to VirusTotal + ARA.

## The Honest Answer

| Dimension | CyberArk EPM | WDAC |
|---|---|---|
| Enforcement | User-mode agent | Kernel-level (ci.dll) |
| Per-user policies | ✅ Yes | ❌ No (per-device only) |
| Cross-platform | ✅ Windows, macOS, Linux | ❌ Windows only |
| Ringfencing | ✅ Network, files, registry | ❌ No |
| Risk engine | ✅ VirusTotal, ReversingLabs | ❌ ISG only |
| Self-service elevation | ✅ Yes | ❌ No |
| Admin can bypass | ✅ Yes (with token) | ❌ No (signed + HVCI) |
| CVE treatment | CyberArk CVEs | MSRC CVEs |
| Cost | Paid | Free (included in Windows) |
| Deployment complexity | SaaS, agent-based, 2-4 weeks | XML/GPO/Intune, 6-9 months, often fails |
| OS update resilience | Broke on Win11 22H2 | Never breaks (same team) |
| Agent dependency | Agent crash = no protection | No agent to crash |
| Post-execution control | ✅ Ringfencing | ❌ No |
| LOLBin protection | ✅ Can block specific LOLBins | ❌ Allows all Microsoft-signed by default |

## The Compromise

- Use Idira for governance + privilege management (per-user, cross-platform, ringfencing)
- Use WDAC for kernel-level enforcement on Windows (admin can't bypass)
- Use both together: WDAC = what CAN run, Idira = what allowed apps can DO

## The Question to Ask

"Are we governing portable/user-context applications, or defending against sophisticated attackers? If it's governance, Idira is the better tool. If it's threat defense, WDAC adds kernel-level enforcement. What's our priority?"


## Reference: essential-eight-compliance.md

# Essential Eight Application Control Compliance Specifics
## Verified via MCP — July 2026

## Maturity Level Requirements

| Level | Acceptable Tool | Key Requirements |
|---|---|---|
| ML1 | AppLocker or WDAC | Workstations only. User profiles + temp folders. Executables, scripts, installers, DLLs |
| ML2 | **WDAC only** | + Internet-facing servers. All locations. Recommended application blocklist. Annual validation. Central logging. Event log protection |
| ML3 | **WDAC only** | + All servers. Driver control. Vulnerable driver blocklist. SIEM integration |

## Why WDAC Is Required at ML2 (Not AppLocker)

AppLocker cannot meet ML2 because:
1. **Driver control** — AppLocker is user-mode only. Can't control kernel drivers.
2. **Recommended application blocklist** — Blocks known LOLBins (mshta.exe, wscript.exe, etc.). AppLocker can't enforce this at kernel level.
3. **Server coverage** — ML2 requires internet-facing servers. AppLocker doesn't cover servers adequately.
4. **All locations** — ML2 requires application control applied everywhere, not just user profiles and temp folders.

Source: Microsoft Learn, "Essential Eight application control" (March 2025). Innitor, "WDAC for Essential Eight" (Feb 2026).

## ISG Explicitly Excluded from Essential Eight

Microsoft's Essential Eight guidance states:

> *"Reputation-Based Intelligence for Application Control does not meet the Essential Eight Application Control due to the requirement 'Organization-approved set' (ISM 1657) and 'Application control rulesets are validated on an annual or more frequent basis' (ISM 1582). This feature within WDAC won't meet the requirements for ML2 or ML3."*

**Implication:** ISG (Option 14) must be set to **Disabled** for ML2/ML3 compliance. Managed installer (Option 13) is recommended to be **Enabled** to assist with policy lifecycle.

Source: Microsoft Learn, "Essential Eight application control" — WDAC policy rules configuration.

## File Path Rules Not Recommended for User Profiles

Microsoft's Essential Eight guidance states:

> *"To meet ISM-1870, Microsoft recommends a defined list of File Publisher Rules or File Hashes have been created within an application control policy. [...] File Path Rules are not recommended for ISM-1870 due to the user having file system permission within user's profile and temporary folders."*

**Implication:** Even Microsoft says: don't use WDAC path rules for user profiles. Use publisher rules and hashes instead. This directly validates the Idira-primary architecture (Idira uses location + publisher + checksum, which is a stronger combination than either alone).

Source: Microsoft Learn, "Essential Eight application control" — ISM-1870 footnote 2.

## ISM Control Mapping

Key ISM controls for application control:

| ISM Control | ML1 | ML2 | ML3 | Description |
|---|---|---|---|---|
| ISM-0843 | Yes | Yes | Yes | Application control on workstations |
| ISM-1490 | No | Yes | Yes | Application control on internet-facing servers |
| ISM-1656 | No | No | Yes | Application control on non-internet-facing servers |
| ISM-1657 | Yes | Yes | Yes | Restrict execution to organization-approved set |
| ISM-1658 | No | No | Yes | Restrict drivers to organization-approved set |
| ISM-1544 | No | Yes | Yes | Microsoft's recommended application blocklist |
| ISM-1870 | Yes | Yes | Yes | Applied to user profiles and temp folders |
| ISM-1871 | No | Yes | Yes | Applied to all other locations |
| ISM-1582 | No | Yes | Yes | Rulesets validated annually |

## Real-World Compliance Rates

- **22%** of Australian federal agencies met Essential Eight ML2 in 2025 (Innitor, Feb 2026)
- Application control was the **key reason** agencies failed to reach ML2
- **<15%** of enterprises have application allowlisting enforced in block mode (Decryption Digest, May 2026)

## WDAC Policy Configuration for Essential Eight ML2

Per Microsoft's guidance, the following WDAC options must be configured:

| Option | Setting | Required For |
|---|---|---|
| Disable Script Enforcement | **Disabled** (scripts enforced) | ISM 1657, 1658 |
| Intelligent Security Graph | **Disabled** | ISM 1657, 1658, 1582 |
| Managed Installer | **Enabled** (recommended) | Policy lifecycle assistance |
| User Mode Code Integrity | **Enabled** | UMCI enforcement |
| Allow Supplement Policies | **Enabled** | Multi-policy format |


## Reference: idira-vs-wdac-capability-reference.md

# Idira EPM vs WDAC — Comprehensive Capability Reference
## Verified via MCP Research — July 2026

## What Each Tool CAN Do

### Idira EPM (CyberArk)

| Capability | Details |
|---|---|
| **Actions** | Allow, Block, Elevate, Elevate-if-necessary |
| **Rule types** | Publisher signature, SHA1/SHA256 checksum, file path (with subfolders), file name, original file name, command-line arguments, parent process, file origin (distributor/updater, URL, location, user), DLL type |
| **Application types** | Executable, DLL, Script (PS1/VBS/JS), MSI/MSP, MSU, ActiveX, Windows App, COM object, Service |
| **Per-user targeting** | AD and AAD users and groups. Per-computer targeting. Up to 1,000 definitions per policy |
| **Cross-platform** | Windows, macOS, Linux |
| **Trusted Sources + Inherited Trust** | Like WDAC Managed Installer but RETROACTIVE — trust applies even to pre-existing files. Trust propagates from installer → installed app → apps installed by that app |
| **Ringfencing (Access Control)** | Control what allowed apps can DO: block internet access, network shares, sensitive files, registry, inter-app launching. Detect mode (audit) + Restrict mode (enforce) |
| **Self-service elevation** | JIT elevation with challenge-response workflows. One-time codes. Manager/IT approval. Auto de-elevation |
| **Greylisting** | "Restrict Access" mode — between Monitor and Default Deny |
| **Script control (macOS)** | Script validation by Team ID + Signing ID (v26.5). Supported: /bin/bash, /bin/csh, /bin/ksh, /bin/sh, /bin/tcsh, /bin/zsh |
| **Discovery** | Application Catalog: full inventory. Events Management: centralized monitoring. Policy automation: auto-detect unhandled apps |
| **QuickStart templates** | Pre-built policies for common roles |
| **Deployment speed** | Northern Trust: 50,000 endpoints in 16 days with zero incidents |

### WDAC (App Control for Business)

| Capability | Details |
|---|---|
| **Enforcement level** | Kernel-level (ci.dll). HVCI-protected when VBS enabled. Cannot be disabled by local admin with signed policies |
| **Rule types** | Publisher (RSA certs, max 4096-bit, NO ECC), Hash (SHA-256), FilePath (admin-write-only by default), FileName (PE OriginalFileName metadata), WHQL, WHQLFilePublisher |
| **Driver control** | Kernel drivers only. EV signer enforcement (Option 8). Vulnerable driver blocklist enabled by default on Win11 22H2+. BYOVD prevention |
| **Managed Installer (Option 13)** | Auto-trust apps installed by Intune/SCCM via NTFS EAs. Child processes inherit trust. NOT retroactive |
| **ISG (Option 14)** | Cloud reputation-based trust. Requires internet. NOT compliant with Essential Eight |
| **Script enforcement** | PowerShell CLM. Block wscript/cscript. mshta/MSXML blocked entirely. COM object enforcement. Cmd.exe .bat/.cmd NOT directly controlled |
| **Dynamic Code Security (Option 19)** | .NET and dynamically loaded libraries. Always enforced in audit mode |
| **Multiple policy format** | Base + Supplemental policies. Deny rules in supplementals silently ignored |
| **Recommended block lists** | Microsoft-maintained driver + application blocklists. Updated via Windows Update |
| **Boot Audit on Failure (Option 10)** | Auto-rollback to audit mode if boot-critical driver fails |
| **Deployment** | Intune, GPO, SCCM, PowerShell. Free (included in Windows 10/11 Pro, Enterprise, Education) |

## What Each Tool CANNOT Do

### Idira EPM Cannot

| Limitation | Severity | Details |
|---|---|---|
| Kernel-level enforcement | CRITICAL | User-mode agent only. Admin can kill agent. Agent crash = all protection ceases |
| Kernel driver control | CRITICAL | Cannot control which drivers load. BYOVD protection requires WDAC |
| Boot-time protection | CRITICAL | Agent starts AFTER boot. Malware loading pre-agent is not blocked |
| Pre-execution blocking (macOS) | MEDIUM | Doesn't intercept ES_AUTH_EXEC. Santa fills this gap |
| OS update breakage | MEDIUM | Win11 22H2/KB5025224 completely broke agent. Win10 KB5023773/KB5025221 also broke agents. Required emergency upgrade |
| Agent conflicts | MEDIUM | Digital Guardian anti-tampering. BitDefender. Microsoft Defender. Chromium browser performance (fixed 26.2.1) |
| Publisher cert expiry | LOW | Stricter than Windows — if signing cert expired, publisher policies fail even when Windows says "Valid" |
| SaaS-only | MEDIUM | On-prem EOL'd Dec 2023. Cloud dependency. Data sovereignty concerns |
| No automatic agent updates | LOW | Must deploy via software distribution |
| ARM limitations | LOW | No elevation restrictions on ARM-32 emulated. Video audit causes unresponsiveness |
| Homebrew (macOS) | LOW | Installation fails with EPM. Needs custom script or path exclusion |
| Intune integration | LOW | "Exclude service accounts" must be DISABLED for system installs |

### WDAC Cannot

| Limitation | Severity | Details |
|---|---|---|
| User-writable FilePath rules | CRITICAL | By design. Refuses FilePath rules for Downloads, Temp, AppData, Desktop. Option 18 disables the guardrail |
| Per-user rules | CRITICAL | Per-device only. AppLocker fills this gap |
| Cross-platform | CRITICAL | Windows only |
| Ringfencing/post-execution | CRITICAL | Controls WHAT runs, not what it does after |
| Self-service elevation | CRITICAL | No elevation workflow |
| LOLBin protection by default | HIGH | "Allow Microsoft" trusts ALL Microsoft-signed binaries including msbuild.exe, InstallUtil.exe, regsvr32.exe, etc. |
| DLL enforcement gap | HIGH | Most deployments leave Dll collection unconfigured. DLL hijacking viable |
| Cmd.exe scripts | MEDIUM | Does NOT control .bat/.cmd execution directly |
| 3rd-party script hosts | MEDIUM | Python/Java/Ruby are "unenlightened" — if host is allowed, all scripts through it are allowed |
| Electron app abuse | MEDIUM | Microsoft-signed Electron apps (Teams, VS Code) bypass via ASAR tampering |
| ECC signatures | LOW | RSA only. ECDSA causes VerificationError = 23 |
| Managed installer gaps | HIGH | Backlog problem, self-updating apps break it, file copy strips EAs, IME injection (fixed), admin can designate MI |
| ISG limitations | MEDIUM | Cloud-dependent. Not Essential Eight compliant. ISG + MI = over-authorization |
| Deployment complexity | CRITICAL | 6-9 month deployments, often fail. <15% enforced in block mode |
| MSI user-writable | MEDIUM | MSI always detected as user-writable on Win10 and Server 2022 and earlier |

## Head-to-Head: Who Wins Each Scenario

| Scenario | Winner | Why |
|---|---|---|
| Block portable app from Downloads | **Idira** | WDAC can't create FilePath rules for user-writable paths |
| Block kernel driver (BYOVD) | **WDAC** | Idira is user-mode, can't control drivers |
| Survive admin compromise | **WDAC** | Signed policies + HVCI survive. Admin can kill Idira agent |
| Ringfencing an allowed app | **Idira** | WDAC has no post-execution control |
| Per-user rules on call center PC | **AppLocker** (or Idira) | WDAC is per-device only |
| Deploy in 2 weeks | **Idira** | SaaS agent. WDAC takes 6-9 months |
| JIT elevation for installer | **Idira** | Self-service workflow. WDAC has none |
| Block LOLBins (msbuild.exe) | **Idira** | WDAC trusts all MS-signed by default |
| Script control (PowerShell CLM) | **WDAC** | Kernel-enforced CLM |
| macOS binary authorization | **Santa** (or Idira) | WDAC is Windows-only |
| Compliance (Essential Eight ML2) | **WDAC** | ASD explicitly requires WDAC for ML2 |
| Free / no vendor dependency | **WDAC** | Built into Windows |
| Developer workstations | **Idira** | Ringfencing allows dev tools while restricting access |
| Agent dependency risk | **WDAC** | No agent to crash, no vendor to go down |
| Application inventory/discovery | **Idira** | Application Catalog + Events Management |
| Auto-trust existing apps | **Idira** | Trusted Sources + Inherited Trust is retroactive (WDAC MI is not) |


## Reference: isg-retirement-and-smart-app-control-2026.md

# ISG Retirement & Smart App Control Status (verified Aug 2026)

Research run 2026-08-05 via MCP (exa advanced search, exa fetch, firecrawl search) + plain web.
User question: is ISG really retired when all MS docs still mention it? What does Microsoft say as
the alternative? Does the reputation data stay in Defender?

## Bottom line
- Only official retirement statement: MC1295285 (Apr 29, 2026), scoped to the Power Platform Graph
  Security connector. No App Control-specific retirement notice exists as of Aug 2026.
- All MS Learn App Control pages still document the ISG option as available (feature-availability
  updated Mar 29, 2026; last content push Apr 28, 2026).
- No public post-cutoff reports of the WDAC ISG option breaking OR still working (Reddit zero hits;
  one deleted MS Q&A thread — ID 5848138).
- Verdict for planning: treat as deprecated-but-not-yet-dead; pilot to verify; never claim "ISG is
  dead" in decks (live docs contradict you). Phrase as: "reputation service deprecated Apr 2026;
  App Control docs unmaintained; no replacement announced; plan for explicit controls."

## The official record
MC1295285 (Microsoft Message Center, published Apr 30, 2026; mirrors: tophhie.cloud
/m365-message-center/message/mc1295285/, m365admin.handsontek.net, app.cloudscout.one
/evergreen-item/mc1295285/, LinkedIn Carsten Groth), verbatim:
"As of April 29, 2026, the Microsoft Graph Security connector has been deprecated and is no longer
supported. This follows the deprecation of the Intelligent Security Graph service that is utilized
for this connector's functionality. ... Remove Microsoft Graph Security connector references from
your flows, apps, and agents, and transition to use the Microsoft Graph Security API."

Related consolidation (same pattern — data persists, API surface consolidates):
- MC1220762 (Jan 2026): MDE + Defender XDR Advanced Hunting APIs retire Feb 1, 2027 -> migrate to
  the Microsoft Graph Security API (v2). Retirement start Feb 6, 2026.
- Graph Security legacy Alerts API v1 retired April 2026 -> v2 (MS Q&A threads, Feb 2026).
- Microsoft Threat Intelligence portal retires Aug 1, 2026; "all Microsoft Threat Intelligence
  capabilities are now available through the Defender portal" (TechRepublic Jul 29, 2026; Petri
  Aug 5, 2026: MDTI convergence GA in Defender portal, standalone Intel Profiles/Explorer/Projects
  retired).

## The three-ISGs naming trap
1. "Microsoft Intelligent Security Graph" (concept / telemetry data plane) — powers all Defender
   products; alive; now branded "Microsoft Defender Intelligent Security Graph" (Eric Lawrence,
   textslashplain.com, Apr 28, 2026).
2. ISG service behind the Power Platform Graph Security connector — RETIRED Apr 29, 2026.
3. Reputation lookup used by WDAC option 14 ("Enabled:Intelligent Security Graph Authorization")
   and by Smart App Control — same service family as #2; still documented; no official status
   statement. Eric Lawrence (Apr 28, 2026, day before the cutoff): "If a code file is unsigned,
   Windows will consult the Microsoft Defender Intelligent Security Graph in the cloud."

## What Microsoft says as the alternative
- For the retired connector: the Microsoft Graph Security API (v2) — MC1295285 verbatim. All
  security data surfaces are consolidating there (MC1220762).
- For App Control: no new reputation feature; ISG remains the ONLY reputation mechanism in the
  feature-availability matrix (Mar 2026). Documented transition path (lightly-managed devices
  starter-policy page): onboard unmanaged apps into Intune, then "transition from ISG to managed
  installer, signed catalog files and/or updated policy rules." SAC developer guidance: "the best
  way to avoid problems ... is to sign your code."

## Does the data stay in Defender? — YES (4 independent lines)
1. SmartScreen AppRep docs actively updated May 4-9, 2026 (post-retirement) — same intelligence.
2. SAC still consults the cloud ISG for unsigned code (Eric Lawrence, Apr 2026).
3. MDE Advanced Hunting FileProfile() global prevalence continues (already used by portable-app
   discovery).
4. MDTI intelligence folded INTO the Defender portal (Aug 1, 2026) — intelligence moves in, not out.

## Smart App Control updates (Apr 2026)
- KB5083769 (April 2026 Patch Tuesday) / Win11 25H2 / Windows Security app v1000.29554+: SAC can
  be RE-ENABLED after being turned off — no reset/reinstall needed. Sources: support.microsoft.com
  SAC FAQ ("Recent Windows updates allow Smart App Control to be re-enabled without requiring
  a..."), Eric Lawrence, gadgethacks. This removes the old "one-way" argument.
- Still consumer-only: auto-starts in Evaluation mode, auto-enables only for good candidates,
  auto-disables on enterprise-managed devices and developer-mode devices; no management surface.
- When SAC is enabled: SmartScreen AppRep is DISABLED and Defender AV enters "hybrid" mode
  (less-active real-time protection) — real security trade-off to cite if anyone proposes SAC
  fleet-wide.
- Blocks MotW'd dangerous file types (39 extensions incl. .ps1 .vbs .js .iso .reg .lnk .msi) from
  ShellExecute with NO override dialog.
- ECC code signing not supported in the CI codepath (being addressed) — avoid ECC for code signing.
- SAC is built on the same CI tech as WDAC; its example policy (SmartAppControl.xml / "Signed and
  Reputable" wizard template) is Microsoft's recommended enterprise starter base policy.

## Research-tooling notes for retirement/deprecation verification
- exa advanced search with includeDomains=[learn.microsoft.com] returned enormous irrelevant
  API-reference pages (multi-hundred-K truncated dumps). Prefer firecrawl_search with
  includeDomains for domain-restricted queries; cap exa numResults / textMaxCharacters.
- Reddit-only exa search: zero results; firecrawl refuses Reddit — use exa snippets for Reddit
  signal.
- Message Center archives (searchable by MC ID): mc.merill.net, tophhie.cloud, cloudscout.one.
- MS Learn URLs drift — re-search on 404 (per triple-check protocol).

## Sources (12; 4 primary/official)
1. MC1295285 (Message Center, Apr 2026) — primary
2. MC1220762 (Message Center, Jan 2026) — primary
3. MS Learn App Control feature-availability (updated 2026-03-29, content 04-28) — primary
4. MS Learn lightly-managed devices starter policy — primary
5. MS Learn use-appcontrol-with-intelligent-security-graph (ISG authorization page)
6. MS Learn Intune manage-app-control (still lists "Trust apps with a good reputation")
7. MS Learn App Control debugging and troubleshooting (still references ISG)
8. MS Learn SmartScreen reputation for Windows app developers (updated May 2026)
9. support.microsoft.com Smart App Control FAQ (re-enable note)
10. textslashplain.com Eric Lawrence "Smart App Control" (Apr 28, 2026)
11. TechRepublic (Jul 29, 2026) + Petri (Aug 5, 2026): MDTI retirement into Defender portal
12. HotCakeX Harden-Windows-Security wiki (Jan 22, 2026): "Signed And Reputable" still described
    as ISG-based, needs reliable internet to reach ISG servers

Gaps: no Reddit signal; one deleted MS Q&A thread (5848138); no published post-cutoff functional
test of the WDAC ISG option. If the ambiguity matters: pilot 50 devices for 7-10 days, watch
CodeIntegrity 3076 (audit) / 3077 (blocked) for whether reputation-based allows actually fire.


## Reference: jamf-vs-santa-workshop-comparison.md

# Jamf Protect vs Santa/Workshop — macOS Application Control Comparison

## Jamf Protect

**What it is:** Apple-native EDR built on Endpoint Security Framework.

**Application control capabilities:**
- Block apps by hash, Team ID, Signing ID
- Custom Prevent Lists: up to 100K entries
- Behavioral detection: JQL analytic rules mapped to MITRE ATT&CK
- Jamf Pro integration: unified MDM + security console

**Limitation:** NOT binary authorization. Default-allow model. Unknown binaries still run.

**Best for:** macOS-first shops, Jamf MDM environments, behavioral detection, compliance baselines.

## Santa + Workshop (North Pole Security)

**What it is:** Purpose-built binary authorization for macOS. Open-source agent (Santa) + commercial management platform (Workshop).

**Binary authorization capabilities:**
- Default-deny in Lockdown mode — unknown binaries don't run
- 5 rule types: CDHash → Binary → Signing ID → Certificate → Team ID
- Transitive allowlisting: approved compilers auto-trust output for 6 months
- Sandbox profiles (2026.5): ringfencing for macOS
- Approval workflows: self-service, designated approvers, social voting
- Risk engine: VirusTotal, ReversingLabs auto-screen unknown binaries
- Package rules: Homebrew, npm, Cargo, GitHub Releases auto-allowlisted

**Limitation:** NOT EDR. No behavioral detection, no threat hunting.

**Best for:** macOS binary authorization, developer workstations, compliance (Essential Eight ML2+), prevention-first security.

## Santa Limitations

- Does NOT block scripts (shell/Python/Ruby bypass Santa) — only binary execution
- Does NOT protect against dlopen/DYLD_INSERT_LIBRARIES (SIP protects when enabled)
- No driver control
- Team ID: ZMCG7MLDV9
- 4 MDM profiles needed: System Extension, TCC, Notifications, Santa Config

## Workshop by North Pole Security

Santa alone = manual rule management per device. Workshop = enterprise management platform built by the same team (Santa's original creators at Google).

**Why Workshop matters:**
- Centralized rule management with sync protocol
- Approval workflows: self-service, designated approvers, social voting
- Risk engine: VirusTotal, ReversingLabs integration
- Package rules: Homebrew, npm, Cargo, GitHub Releases, VS Code extensions, Terraform
- File access authorization — control which processes can read/write sensitive files
- USB/SD blocking — prevent data exfiltration via removable media
- Telemetry with SQL queries + management zones + audit trails
- SOC 2 compliant. Cloud-hosted or self-hosted.
- Private sync protocol (faster than open-source sync servers)
- $4M seed from Andreessen Horowitz (2025)

**Alternatives to Workshop (open-source sync servers):**
- Moroz: simple golang server, hardcoded rules
- Rudolph: AWS-based serverless (API GW + DynamoDB + Lambda)
- Zentral: event hub with Santa management
- Fleet: GitOps-native device management with Santa support

## Recommendation

**Santa/Workshop for binary authorization (prevention) + Jamf Protect or CrowdStrike for EDR (detection).**

They complement each other:
- Santa blocks what shouldn't run (pre-execution)
- Jamf/CrowdStrike catches what slips through (post-execution behavioral detection)

## CrowdStrike Falcon for macOS

- Cross-platform EDR with macOS-specific heuristics
- Uses Endpoint Security Framework (same as Santa) — can coexist
- Application control via custom blocking (hash, signing info)
- Script-based execution monitoring
- Enhanced network visibility (sensor 7.29+)
- Pricing: $60-240/endpoint/year

## Key Deployment Considerations

- Santa: Deploy via Jamf as Installer Package (.pkg). Jamf supports "Audit and Enforce" mode.
- Workshop: Cloud-hosted or self-hosted. Integrates with Jamf, Intune, and more.
- CrowdStrike: Deploy via Jamf as Custom App. System Extension and Network Extension profiles needed.
- All three use Endpoint Security Framework — can coexist on same device.


## Reference: portable-app-discovery-mde.md

# Portable App Discovery via MDE Advanced Hunting

## The Provenance Approach (Not Exclusion Lists)

Traditional approach: filter OUT known-good software (vendor names, paths, hashes).
This fails at scale — maintenance burden, stale lists, missed edge cases.

**Provenance approach**: filter IN files introduced by the user. Ask "how did this file arrive?"
rather than "is this file on my allowlist?"

DeviceFileEvents captures both the download origin (FileOriginUrl from Zone.Identifier ADS,
parsed from HostUrl field) and the creating process (InitiatingProcessFileName).

A file created by chrome.exe → user downloaded it.
A file created by outlook.exe → email attachment.
A file created by 7z.exe / explorer.exe (zip) → extracted archive.
A file created by SYSTEM / msiexec / TrustedInstaller → deployed by IT — auto-excluded.

## MCP-Verified Signals (July 2026)

### KQL-Side Detection Signals
1. **FileOriginUrl** — Zone.Identifier HostUrl. Coverage: Edge, Chrome, Firefox, Outlook, Office, WinRAR. NOT: 7-Zip, PeaZip (strip MOTW).
2. **InitiatingProcessFileName (create)** — which process CREATED the file. Source: DeviceFileEvents.
3. **ProcessIntegrityLevel = "Low"** — kernel MOTW detection at execution time. Source: DeviceProcessEvents. FREE signal, more reliable than FileOriginUrl (survives 7-Zip extraction in some cases).
4. **DeviceTvmSoftwareInventory absence** — not in Defender Vuln Mgmt known software. TVM table only available in Defender XDR AH, NOT Sentinel.
5. **SmartScreen events** — SmartScreenAppWarning + SmartScreenUserOverride in DeviceEvents. AdditionalFields.Experience = severity reason.

### Enrichment Joins (KQL)
6. **AlertEvidence** — has this SHA1 triggered any Defender alerts? EntityType="File". Automatic, no config needed. Returns DefenderAlerts, IsMalwareAlert, AlertTitles.
7. **DeviceNetworkEvents** — where does the app connect? InitiatingProcessSHA1 join. Returns NetworkConnections, TopDestUrls, TopDestIPs, TopDestPorts. Heavy join — remove if timeout.
8. **ParentProcess + CommandLine** — who launched it, with what args. Already in DeviceProcessEvents, just project it. FREE.
9. **DeviceFileCertificateInfo** — IsSigned, IsTrusted, Signer, Issuer, IsRootSignerMicrosoft.

### PowerShell Enrichment
- **VirusTotal** — hash lookup via VT API v3. Free tier: 500/day.
- **Growth/trending** — compare two CSV runs to detect New/Growing/Stable/Declining.

## Dead Ends (Verified Not to Work)

- **DeviceRegistryEvents** — MDE only tracks HKLM, not HKCU. Portable apps write to HKCU exclusively. Dead end.
- **DeviceImageLoadEvents** — DLL loading from AppData. False-positive magnet: Electron apps (Teams, Slack, VS Code), game launchers, dev tools. Not worth the noise.
- **DeviceTvmSoftwareEvidenceBeta** — beta table with DiskPaths/RegistryPaths. Watch for GA.

## Key API Limits

- **FileProfile()**: caps at 1000 records per invoke. Use SHA1 (SHA256 "usually not populated").
- **Advanced Hunting API**: 10-min timeout, 100K row limit, 50MB response limit.
- **Single-file API** (GET /api/files/{sha1}): 100 calls/min, 1500 calls/hr.
- **AH API for FileProfile batches**: build datatable of hashes, invoke FileProfile, ~7s between queries to avoid throttling.

## Performance at 15k+ Devices

- 30-day windows recommended. 90 days risks timeout — run 3 × 30-day queries, concatenate CSVs.
- hint.shufflekey = SHA1 on all high-cardinality summarize and join operations.
- Use `has` (indexed) not `contains` (substring scan) for path filters.
- The known-vendor CompanyName pre-filter kills ~40% of rows before summarize — biggest single performance win.
- DeviceNetworkEvents join is the heaviest — remove first if approaching timeout.

## Scoring Model

No composite scores — the weighted Portability/Risk composites were dropped (they overfit and misled: signed+prevalent shadow IT scored 0). What remains:
- **Raw fact columns** (signed, trust, prevalence, vendor, path, users)
- **Boolean flags** (PERSISTENCE, SCRIPT_LAUNCHED, RENAMED_LOLBIN, ...)
- **RedFlagCount**: an UNWEIGHTED tally of independent red-flag booleans — "how many reasons to look", sort by it
- **Buckets**: Loud (threat-shaped signal) / RedFlagged (count >= 2) / Internal / New / Installer / Stable
- **Decision carry-over** from PreviousCsv (vet once, track state) + Growth KPI vs the previous run

## Reference Implementation

Full PowerShell script + KQL queries in the session artifact:
`~/portable-app-discovery.ps1`

Three committed KQL queries:
- `provenance.kql` — core discovery query (fast, fewer columns; raw column names per the PS1 contract).
- `provenance-full.kql` — full enrichment: TVM anti-join, SmartScreen, AlertEvidence, DeviceNetworkEvents, cert info, persistence (HKLM Run keys + schtasks).
- `provenance-governance.kql` — governance/vetting pass: completeness-first, no DistinctDays filter (one-shot tools need vetting too).


## Reference: portable-app-discovery-methodology.md

# Portable App Discovery Methodology (MCP-Verified, July 2026)

## Approach: Provenance-Based (Not Exclusion-Based)

The user explicitly rejects exclusion-list approaches ("spaghetti code exclusion").
Instead: filter IN files introduced by the user. MDE's `DeviceFileEvents` captures
both download origin (`FileOriginUrl` from Zone.Identifier ADS) and the creating
process (`InitiatingProcessFileName`).

### The Core Join

```
DeviceFileEvents (FileCreated by chrome/firefox/outlook/7z/explorer)
    ↓ INNER JOIN on (DeviceName, SHA1)
DeviceProcessEvents (actually executed from user-writable paths)
    ↓
Candidates — no exclusion lists needed
```

### Five Independent Provenance Signals

| # | Signal | Source | MDE Column | Boost |
|---|---|---|---|---|
| 1 | FileOriginUrl | DeviceFileEvents | FileOriginUrl | +1.5 |
| 2 | InitiatingProcessFileName | DeviceFileEvents | InitiatingProcessFileName | +0.5–1.5 |
| 3 | ProcessIntegrityLevel = Low | DeviceProcessEvents | ProcessIntegrityLevel | +1.0 |
| 4 | Not in TVM Inventory | DeviceTvmSoftwareInventory | Anti-join | +1.0 |
| 5 | SmartScreen Warned/Overrode | DeviceEvents | ActionType | +1.5–2.0 |

### Signal Details

**Signal 1 — FileOriginUrl (Zone.Identifier HostUrl):**
Parsed from Mark of the Web alternate data stream. Populated by Edge, Chrome,
Firefox, Opera, Brave, Outlook, Office, WinRAR (v6+), and Windows built-in zip
(explorer.exe). NOT populated by 7-Zip or PeaZip (strip MOTW). Verified via
Microsoft Tech Community blog (July 2018).

**Signal 2 — InitiatingProcessFileName:**
The process that CREATED the file. Browsers/email/tools = user-introduced.
SYSTEM/msiexec/TrustedInstaller = deployed by IT. This automatically excludes
everything deployed via Intune/SCCM and everything auto-updated.

**Signal 3 — ProcessIntegrityLevel:**
Windows kernel assigns "Low" integrity to processes from internet-downloaded files
(MOTW present at runtime). FREE — already in DeviceProcessEvents. Unlike
FileOriginUrl, integrity level is kernel-enforced; works even when 7-Zip
strips Zone.Identifier.

**Signal 4 — DeviceTvmSoftwareInventory Anti-Join:**
Defender Vuln Mgmt known-software inventory. File NOT in this table → invisible
software → strong portable signal. Replaces "check Add/Remove Programs."
IMPORTANT: NOT available in Sentinel — only in Defender XDR Advanced Hunting.

**Signal 5 — SmartScreen Events:**
`SmartScreenAppWarning` / `SmartScreenUserOverride` in DeviceEvents. User clicking
"Run anyway" = strongest provenance signal. `AdditionalFields.Experience` =
Untrusted/Phishing/Malicious/Exploit/CustomBlockList.

### What This Automatically Excludes (No Lists Needed)

- Everything deployed via Intune/SCCM (SYSTEM/msiexec-created — not in initiator filter)
- Everything auto-updated (Teams→Teams, Chrome→Chrome — no browser initiator, no FileOriginUrl)
- One-shot installers (DistinctDays ≤ 1)
- Everything from C:\Windows, C:\Program Files (path filter)
- Everything Microsoft-root-signed (scored to 0 by FileProfile)

### Multi-Dimensional Scoring — SUPERSEDED (kept for history)

The original model was a single weighted composite (path × persistence × prevalence
× trust → tiers). It FAILED: known portable apps (mouse jiggler, GlobalPrevalence
665K) scored 1.98 because trust=0 cancelled path risk. Discovery is NOT risk scoring.
DO NOT revert to this model. Use the two-score model below.

```text
OLD (superseded):
Composite = PathRisk×0.25 + Persistence×0.30 + Prevalence×0.25 + Trust×0.20
Tiers: ≥ 7.5 = Tier 1 (review), ≥ 5.0 = Tier 2 (sample), < 5.0 = Tier 3 (archive)
```

### Two-Score Model (Current — Portability + Risk)

- **Portability (0-10):** path base (×0.5) + provenance boost (FileOriginUrl +2,
  browser initiator +2, Low integrity +1, not-in-TVM +1) + usage (30d +2, 10d +1.5,
  3d +1, else +0.5). Cap 10. Sort the inventory by this.
- **Risk (0-10):** additive, capped 10:
  - Signing/prevalence: ThreatName +5; GP=0 & unsigned +4; GP<100 & unsigned +3;
    GP<10K +1; MS-root/ubiquitous +0. (CertInfo fallback: unsigned +4, signed +2,
    signed+trusted +1.) No data +2.
  - SmartScreen UserOverride +3 / AppWarning +2
  - DefenderAlerts: malware +5, ≥3 +3, >0 +2
  - Network connections +1; script parent +2
  - **Renamed binary (T1036.003):** PE OriginalFileName ≠ FileName. Renamed LOLBin
    (certutil, powershell, rundll32, mshta, wscript, cscript, regsvr32, msbuild,
    psexec, bitsadmin, wmic, cmd, reg, schtasks) +5; renamed regular tool +1.
  - **Command line (ExampleCommandLine):** download cradle (certutil -urlcache,
    bitsadmin /transfer, Invoke-WebRequest, iex) +3; encoded (-enc, base64) +3;
    LOLBin invocation (rundll32, mshta, regsvr32 /s) +2.
  - **PersistenceDetected (KQL join, HKLM Run keys + schtasks → user-writable path
    referencing candidate):** +4.
- Buckets: Portable+Risky / Portable / Risky / Low signal. ONE merged CSV with a
  Bucket column (user prefers merged output).
- **Flags column:** script appends per-row flag strings (RENAMED_LOLBIN:certutil.exe,
  DOWNLOAD_CRADLE, ENCODED_CMD, PERSISTENCE...) so scores are explainable at a glance.
- All extra signals degrade gracefully: missing CSV columns → signal skipped, no errors.

### GlobalPrevalence Trust Tiers

| GlobalPrevalence | Signed/Valid | Unsigned/Invalid |
|---|---|---|
| IsRootSignerMicrosoft | 0 | 0 |
| ≥ 100,000 | 0 | 2 |
| 10,000–99,999 | 1 | 3 |
| 1,000–9,999 | 2 | 5 |
| 100–999 | 4 | 6 |
| 10–99 | 7 | 7 |
| 1–9 | 8 | 8 |
| 0 (never seen) | 9 | 9 |
| ThreatName populated | 10 | 10 |

### FileProfile() Enrichment

**AdvancedHunting API (fast):** `datatable(...) | invoke FileProfile("SHA1", 1000)`.
Batch of 1000, seconds each. Cap: 1000 per invoke. 7s delay between batches.
Returns: GlobalPrevalence, Signer, Issuer, Publisher, IsCertificateValid,
IsRootSignerMicrosoft, SignatureState, ThreatName, ProfileAvailability.

**Single-File API (slow):** `GET /api/files/{sha1}`. 90/min safe, 1400/hr.
Also returns: determinationType (Malicious/Suspicious/Clean/Unknown/Pua).

**Offline (no API):** Uses DeviceFileCertificateInfo columns from KQL export,
ProcessVersionInfoCompanyName from version resources, or local fleet prevalence.

### KQL Performance (15k+ Devices, All MCP-Verified)

- `hint.shufflekey = SHA1` on high-cardinality summarize/join
- Use `has` (indexed) not `contains` (substring scan) for paths
- 30-day windows max. 90-day scans hit 10-min AH timeout. Split into 3×30d.
- Time-filter DeviceFileCertificateInfo join: `| where Timestamp > ago(90d)`
- DeviceTvmSoftwareInventory NOT in Sentinel — run Version A+ in Defender XDR AH
- The INNER JOIN on (DeviceName, SHA1) between FileEvents and ProcessEvents is
  the performance-critical step. The FileEvents side is already small (only
  FileCreated from user-facing processes).

### Known Dead Ends

- **DeviceRegistryEvents:** MDE only tracks HKLM, not HKCU. Portable apps use HKCU.
- **DeviceImageLoadEvents:** DLL loading from AppData = Electron false-positive magnet
  (Teams, Slack, VS Code). Not worth the noise.
- **DeviceTvmSoftwareEvidenceBeta:** Beta, covered by stable DeviceTvmSoftwareInventory.

### Additional Enrichment (Separate KQL Queries, Not In Script)

1. **Defender Alerts** — `AlertEvidence` joined on SHA1. Has this file triggered alerts?
2. **Network Beaconing** — `DeviceNetworkEvents` on InitiatingProcessSHA1.
3. **Growth/Trending** — Compare DeviceCount across two time windows.
4. **Parent Process Chain** — `InitiatingProcessParentFileName`.

### Artifact

- `~/portable-app-discovery.ps1` — no-score pipeline (facts + flags + RedFlagCount; the old Portability/Risk composites were dropped).
  Pure CSV processor: -InputCsv / -OutputCsv / -PreviousCsv; buckets (Loud / RedFlagged / Internal / New / Installer / Stable);
  Decision carry-over and Growth KPI vs the previous run. The API path (KQL via Advanced Hunting API + FileProfile enrichment) lives in the MDE skill's one-shot runner.
  NO KQL embedded in the script — here-string collision (see pitfalls in SKILL.md).
- `provenance.kql` — core query (fast, fewer columns).
- `provenance-full.kql` — full enrichment: TVM anti-join, SmartScreen, AlertEvidence,
  DeviceNetworkEvents, cert info, persistence (HKLM Run keys + schtasks).
- Copies land in `C:\Users\<user>\Downloads\`.


## Reference: portable-app-discovery-pipeline.md

# Portable App Discovery Pipeline (KQL + PowerShell)

## Core Insight: Provenance, Not Exclusion Lists

Instead of filtering OUT known-good software (exclusion lists that rot), filter IN files
introduced by the user. MDE's DeviceFileEvents captures both the download origin
(FileOriginUrl from Zone.Identifier ADS) and the creating process (InitiatingProcessFileName).

A file created by chrome.exe → user downloaded it.  
A file created by outlook.exe → email attachment.  
A file created by SYSTEM/msiexec → deployed by IT. No exclusion lists needed.

## Provenance Signals (MCP-verified, July 2026)

1. **FileOriginUrl** — Zone.Identifier HostUrl. Populated by Edge, Chrome, Firefox, Outlook, WinRAR. NOT by 7-Zip/PeaZip (strip MOTW). Source: DeviceFileEvents.
2. **InitiatingProcessFileName** — which process CREATED the file. Browsers/email/tools = user-introduced. SYSTEM/msiexec = deployed. Source: DeviceFileEvents.
3. **ProcessIntegrityLevel** — "Low" means Windows kernel detected MOTW at execution. FREE signal. Source: DeviceProcessEvents.
4. **DeviceTvmSoftwareInventory absence** — NOT in Defender Vuln Mgmt inventory = invisible software (not in Add/Remove Programs equivalent). Anti-join. NOTE: NOT available in Sentinel, only Defender XDR AH.
5. **SmartScreen events** — SmartScreenAppWarning (flagged) and SmartScreenUserOverride (human clicked through). Source: DeviceEvents.
6. **AlertEvidence** — has this file triggered Defender alerts? EntityType="File" join on SHA1. Source: AlertEvidence table.
7. **DeviceNetworkEvents** — outbound connections. Where does this app phone home? Source: DeviceNetworkEvents (heaviest join, remove if timeout).
8. **ParentProcess + CommandLine** — who launched it? explorer.exe = user double-click. cmd/powershell = scripted. Source: DeviceProcessEvents.

## Dead Ends (MCP-verified)

- **DeviceRegistryEvents**: MDE only tracks HKLM, not HKCU. Portable apps only write to HKCU. Dead end. (Persistence detection therefore only catches HKLM Run keys + schtasks — user-level Run keys are invisible.)
- **DeviceImageLoadEvents (fleet-wide)**: Electron apps (Teams, Slack, VS Code) are massive false-positive sources. NOT worth the noise fleet-wide.
- **DeviceImageLoadEvents (candidate-scoped)**: VIABLE — see SIDELOAD_DLL below. Scoping to candidates (exe in user-writable path loading an unsigned DLL from its own directory) avoids the Electron FP magnet.
- **Packer/entropy detection (T1027.002)**: MDE Advanced Hunting does NOT expose PE section names or entropy — requires the actual file bytes. Run `packdetect` / `sigcheck` at review time when the file is retrieved via EPM/EDR. Not pipeline-able from AH telemetry.

## KQL Query Design for 15k+ Devices

### Performance requirements
- 10-minute hard timeout (MCP-verified, not configurable)
- hint.shufflekey on high-cardinality summarize columns (SHA1)
- Use `has` (indexed) not `contains` (substring scan)
- 30-day windows recommended. 90 days → split into three 30-day queries.
- DeviceFileEvents filtered by InitiatingProcessFileName is a SMALL subset — key efficiency win.
- The INNER JOIN between creation and execution on (DeviceName, SHA1) is the bottleneck.
- DeviceNetworkEvents join is heaviest — remove first if approaching timeout.

### Query structure
```
DeviceFileEvents (FileCreated by browsers/email/tools)
    ↓ INNER JOIN on (DeviceName, SHA1)
DeviceProcessEvents (executed from risky paths)
    ↓ LEFT JOIN: TVM, SmartScreen, Alerts, Network, Cert
    ↓ Roll up to file-level
Candidates
```

### PowerShell scoring — TWO-SCORE MODEL (user-corrected, July 2026)
The original weighted composite (path × persistence × prevalence × trust) was REJECTED:
it buried known portable apps (mouse jiggler, GlobalPrevalence 665K → composite 1.98).
Discovery is NOT risk scoring. "Safe" ≠ "not portable."

- **Portability (0-10)**: how confident this is a portable app.
  pathBase(×0.5) + provenance signals (FileOriginUrl +2, browser initiator +2, mail +1.5,
  archive/copy +1, Low integrity +1, not-in-TVM +1) + usage (30d+ =2, 10d+ =1.5, 3d+ =1, else 0.5).
  Cap 10. SORT BY THIS.
- **Risk (0-10)**: how worried to be. Unsigned/unknown +2-4, SmartScreen override +3 / warning +2,
  Defender alerts +2-5 (malware +5), network +1, script parent +2 / unusual +1. Cap 10.
  REVIEW BY THIS.
- Buckets: Portable+Risky (both ≥6), Portable, Risky, Low signal. ONE merged CSV with Bucket column.
- No weights to tune, no tier thresholds — the user rejected both.
- **NO decision tracking in the script** (user rejected twice): no Decision/Status columns,
  no `-DecisionsCsv` param. The script outputs the scored inventory; vetting/approval happens
  in the user's separate governance process. Do not re-add.

## Two Query Shapes: DISCOVERY vs GOVERNANCE (July 2026)

The provenance gate makes discovery PRECISE but INCOMPLETE. For vetting/approval the goal is
completeness — the provenance query misses files created before the lookback window, files
extracted by unlisted tools (NanaZip, Bandizip), files copied from shares/USB via script,
and setup.exe installers (deliberately excluded). User's actual concern: "lots of stuff we
may need to vet/approve, not necessarily malware."

| | provenance.kql (discovery) | provenance-governance.kql (vetting) |
|---|---|---|
| Gate | User-introduced only (browser/mail/archive initiator) | Path-based completeness — nothing excluded |
| Filter | provenance INNER JOIN | Vendor-noise pre-filter only (CompanyName !in Microsoft/Google/Adobe/...) |
| Installers | excluded (setup/install) | INCLUDED — installers are governance events |
| One-shots | distinct-days filter removed, persistence scores them | Included |
| Output | ~500 items | 1,000-3,000 items |
| Use | "Who's running downloaded stuff?" | "What needs review?" — the default for governance |

Rule: when the goal is vetting, run the governance query; provenance becomes a SCORING SIGNAL
(portability), not a filter. KQL file: `provenance-governance.kql` (single DeviceProcessEvents
pass, no joins — cheap enough for 90-day windows on 15k+ fleets).

## Initiator Classes (July 2026 — KQL case() classification)

The initiator filter evolved from a flat name list to CLASSES, so the provenance boost is
per-class and previously-invisible droppers are caught. In `DeviceFileEvents` FileCreated:

| Class | Initiators | Portability boost |
|---|---|---|
| Browser | chrome, firefox, msedge, iexplore, opera, brave | +2.0 |
| Email | outlook, thunderbird | +1.5 (KQL class +2.0) |
| Archive | 7z, 7zFM, WinRAR, peazip | +1.0 |
| Explorer | explorer, wget, curl | +1.0 |
| **OfficeMacro** | winword, excel, powerpnt, msaccess, visio, mspub | **+3.0** — Word/Excel legitimately writing an exe is the spear-phishing pattern (T1137.001, FIN7/AgentTesla/PlugX) |
| **ScriptHost** | powershell, pwsh, cmd, wscript, cscript, mshta, rundll32 | **+2.5** — script-dropped exe |

Anything not in a class (`Other`) is dropped at KQL level. `ExampleInitiatorClass` column
flows through to the CSV; old CSVs degrade gracefully.

## Extra Risk Signals (July 2026, free — columns already in KQL output)

- **Renamed binary (T1036.003):** PE `OriginalFileName` vs `FileName`. Renamed LOLBin
  (certutil, powershell, rundll32, mshta, wscript, cscript, regsvr32, msbuild, psexec,
  bitsadmin, wmic, cmd, msiexec, reg, schtasks) = +5 risk. Renamed regular tool = +1.
- **Command-line patterns** (ExampleCommandLine): download cradles (`certutil -urlcache`,
  `bitsadmin /transfer`, `iwr`, `iex`, `start-bitstransfer`) = +3; encoded commands
  (`-enc`, `frombase64string`) = +3; LOLBin invocation (`rundll32`, `mshta`, `regsvr32 /s`,
  `msbuild *.xml`) = +2.
- **Persistence (T1547.001/T1053.005):** HKLM Run/RunOnce value pointing at a candidate
  (join on parsed exe name) or `schtasks /create /tr` → user-writable path = +4.
  CAVEAT: MDE tracks HKLM only — HKCU Run keys invisible (confirmed via Microsoft docs).
- **IsAITool (shadow AI governance):** FileName/CompanyName/ProductName match against known
  AI tools (claude, codex, cursor, copilot, ollama, openclaw, gemini, windsurf, devin, kiro,
  antigravity, goose, cline, roo-code, junie, warp, chatgpt, perplexity, poe, lm studio,
  llama, aider, continue + vendors anthropic/openai/google/mistral/anysphere/cursor).
  Flag `AI_TOOL`, ZERO risk change — it's a governance conversation, not malware.
  MDE native source coming: `AIAgentsInfo` table (Platform == "LocalAgents"), prerelease —
  this name-list is the today-version.
- **NonStandardPorts (cheap beaconing proxy):** TopDestPorts minus {80,443,53,8080} non-empty
  = +1 risk, flag `NONSTD_PORT`. Full beaconing (jitter/series_decompose_anomalies) is too
  heavy per-file — this is 80% of the value at 5% of the cost.
- **NO_METADATA:** empty CompanyName + unsigned = +1 risk.
- **SPOOFED_METADATA (T1036.001):** CompanyName claims a spoofable vendor (Microsoft
  Corporation, Google LLC, Adobe Inc, Apple Inc, Oracle America) but the file is NOT actually
  signed (`IsSigned != True` / `IsCertificateValid != True`) = +4 risk. Regin/BADNEWS pattern —
  free check in PowerShell from cert-join columns. Naive "Publisher: Microsoft" display trust
  is exactly what attackers exploit.
- **OFFICE_DROP (T1137.001):** `ExampleInitiatorClass == "OfficeMacro"` = +3 risk.
- **SIDELOAD_DLL (T1574.002):** candidate exe loads unsigned DLLs from its OWN directory
  (`DeviceImageLoadEvents` join: InitiatingProcessSHA1 = candidate, DLL dir == exe dir,
  IsSigned != True via DeviceFileCertificateInfo) = +3 risk. Candidate-scoped only — fleet-wide
  version is an FP magnet (Electron bundles unsigned DLLs in AppData).
- **FirstSeenAny:** carry FileCreationTime through the creation join (DeviceFileEvents
  Timestamp projected as FileCreationTime) so "brand new" vs "been here for years" is
  sortable — new files get reviewed first.
- **Flags column:** script appends human-readable flag strings per row so every score is
  explainable (RENAMED_LOLBIN:certutil.exe ENCODED_CMD PERSISTENCE AI_TOOL ...).

## PowerShell Implementation Notes

### Critical: KQL in separate files, NOT embedded here-strings
PowerShell here-strings (`@"..."@`) nested with KQL verbatim strings (`@"AppData\Local\"`) cause
unrecoverable parse errors. ALWAYS store KQL in separate `.kql` files and load with
`[IO.File]::ReadAllText()`. This follows Microsoft's official MDE PowerShell API samples.

### Auth methods (no app registration needed)
The script tries in order: `$env:MDE_TOKEN` → app registration params → `Get-AzAccessToken` (Az module) → `az account get-access-token` (Azure CLI). `Connect-AzAccount` or `az login` are sufficient — no Azure AD app registration required for interactive use.

### Official Microsoft API patterns to follow
- Auth body: `[Ordered] @{ resource = "..."; client_id = "..."; ... }`
- Query body: `ConvertTo-Json -InputObject @{ Query = $kql }`
- API calls: `Invoke-WebRequest -Method Post ...` (better error handling than Invoke-RestMethod)
- Complex KQL: `$query = [IO.File]::ReadAllText("C:\myQuery.txt")`

### The patch tool is brittle with .ps1 files
The `patch` tool's fuzzy matching (9 strategies) consistently fails on PowerShell files
due to backticks, variable interpolation, and incremental edits shifting line numbers.
Prefer `write_file` for clean rewrites, or use `terminal` with `sed`/`python3` for
exact string replacements. Verify with PowerShell's parser before delivering.

### PowerShell parse pitfalls (all hit in production debugging, July 2026)
- **`$var (` inside a double-quoted string breaks parsing** — e.g. `"... ($enriched with detections)"`.
  PowerShell tries to parse `(...)` after variable expansion. Use format strings instead:
  `Write-Host ("  VT {0}/{1} ({2} with detections)" -f $done, $total, $enriched)`.
- **`if/elseif` as a hashtable value does not parse.** Compute the verdict BEFORE the hashtable:
  `$verdict = "Unknown"; if (...) { $verdict = "X" }` then `@{ VTVerdict = $verdict }`.
- **Trailing comma on the LAST param in a param block** = "Missing expression after ','".
  Param comment lines with `# ----` separators invite this — check the final param has no comma.
- **`Sort-Object Portability -Descending, Risk -Descending` is invalid.**
  Use `Sort-Object @{Expression="Portability";Descending=$true}, @{Expression="Risk";Descending=$true}`.
- **`PSParser::Tokenize` does NOT throw** — it collects errors into a `[ref]` array. Passing
  `[ref]$null` silently discards them and reports a false "parse OK". Always check `$errors.Count`.
  Validate a script before delivery: `powershell.exe -Command ". 'path.ps1' -Mode Offline -InputCsv test.csv"`
  (real execution beats tokenize-based checks).
- **Nested here-strings are unrecoverable**: KQL's `@"AppData\Local\"` (Kusto verbatim strings)
  inside a PowerShell `@"..."@` heredoc confuses the parser. KQL belongs in `.kql` files.

### Auth notes
- `Connect-AzAccount` and `az login` are DIFFERENT auth stacks — if one fails with cert/trust
  errors, the other often works. Subscription choice is irrelevant for MDE API (not subscription-scoped);
  pick any. Tenant = the one where security.microsoft.com works for the user.
- Az.Accounts 5.x (Az 14+) returns `Get-AzAccessToken` tokens as SecureString — unwrap:
  `[System.Net.NetworkCredential]::new('', $azToken.Token).Password`.
- MDE API legacy resource: token audience must be `https://api.securitycenter.microsoft.com`
  even when calling `https://api.security.microsoft.com` endpoints (403 if mismatched).


## Reference: portable-app-governance-research.md

# Portable App Governance Research (July 2026)

## Key Finding: Idira EPM is the Primary Governance Tool

Research across enterprise practice revealed that EPM tools are the standard for portable app governance, not WDAC.

## Evidence

### WDAC Limitations for Portable Apps
- WDAC refuses to create FilePath rules for user-writable directories (Downloads, %LOCALAPPDATA%) — by design
- Less than 15% of enterprises have WDAC enforced in block mode (Decryption Digest, 2026)
- WDAC deployments take 6-9 months and often fail
- Common failure: deploy enforce mode without adequate baseline data, followed by user-impacting blocks, followed by rollback
- Only 22% of Australian federal agencies met Essential Eight ML2 in 2025, application control was key reason (Innitor)

### What Enterprises Actually Do
- Northern Trust: 50,000 endpoints deployed CyberArk EPM in 16 days with zero incidents
- IIFL Group: financial services, application control + least privilege
- Persistent Systems: 3,000 developers, application control
- Elanco: 7,000 endpoints, centralized application management
- Arcelik: 1,500 workstations, application control policies
- 25,000-seat financial organization reached 80% WDAC enforcement in 6 months (needed external help from AppControl.ai)

### What Other EPM Vendors Do
- **Ivanti**: Trusted Ownership model — files placed by SYSTEM/admin are allowed, user-introduced content denied by default. "A portable application is copied into the user profile. Ivanti blocks it because it is user-owned."
- **ThreatLocker**: Learning Mode + Ringfencing™ — hash-based detection, controls file/registry/network access. "Portable apps are often missed during patch cycles, creating hidden vulnerabilities."
- **BeyondTrust**: QuickStart templates + Trusted Ownership — pre-configured policies for different flexibility levels. Has specific documentation on "Using Endpoint Privilege Management with local AI agents."

### CyberArk's 3-Layer Framework for Portable Apps
From CyberArk community article "EPM - How to Contain User-Based Applications":
- **Layer 1: Risk-reduction controls** — restrict all user-based apps from invoking sensitive OS components commonly abused by attackers or leveraged by Agentic AI
- **Layer 2: Allowlist for approved user-based apps** — Location (%USERPROFILE%) + Publisher + Original Filename + Checksum
- **Layer 3: Discovery and default-deny** — discover first, then enforce

CyberArk's own words: "These portable-apps are growing in popularity especially with the proliferation of Agentic AI. AI solutions such as Claude, Cursor, and many others all can be installed within a user profile and be utilized for privilege escalation via relatively trivial mechanisms."

### Santa + Workshop for macOS
- Santa: open-source binary authorization (pre-execution blocking via ES_AUTH_EXEC)
- Workshop: enterprise management platform (centralized rules, approval workflows, risk engine, package rules)
- Sandbox profiles (2026.5): ringfencing for macOS — confine binaries to least-privilege profiles
- Transitive allowlisting: approved compilers auto-trust output for 6 months
- Limitation: doesn't block scripts (shell/Python/Ruby bypass Santa)

## The Recommended Architecture
- **Idira EPM**: Primary governance tool (portable apps, privilege management, ringfencing, cross-platform, self-service elevation)
- **WDAC+AppLocker**: Minimal scope only (kernel drivers, PowerShell CLM)
- **Santa + Workshop**: macOS binary authorization (pre-execution blocking)
- **Jamf Pro**: macOS MDM (deploy Santa, configure Idira)

## Diplomatic Framing
When presenting the shift from "WDAC for everything" to "Idira for governance":
- NEVER say "WDAC can't handle portable apps" or "we were wrong"
- ALWAYS say "WDAC was designed for kernel enforcement and compliance — not portable app governance. Our existing CyberArk EPM has a purpose-built framework for this exact problem. This is the right tool for the right job."
- Frame as evolution, not correction


## Reference: portable-app-options-triple-check-2026-08.md

# Portable App Management — What Orgs Do (Triple-Check, Aug 2026)

Fresh 3-pass MCP verification (Exa broad search -> Firecrawl search/scrape -> primary
sources). Trigger: user asked for a "triple check" on what orgs do to manage portable
apps, "disregard previous conversations, use mcp". All claims below carry their
verification count from THIS run (independent sources, not seller pages).

## Verified consensus (each claim 3+ sources in this run)

1. Discovery before enforcement. CIS Control 2 ("Inventory and Control of Software
   Assets"): only authorized software installs AND executes; unauthorized is found and
   prevented. Vendors converge on the same sequence: audit/learning mode -> allowlist
   the legit stuff -> default-deny the rest (MS Learn design guide audit mode, CyberArk
   Layer 3, ThreatLocker Monitor-Only mode).
2. Tiered policy by device class, not one org-wide policy. MS Learn
   common-appcontrol-use-cases: fully managed (strict allowlist + managed installer),
   lightly managed (kernel protection + signed/reputable/MI allow), fixed-workload
   kiosks (full lockdown), BYOD (blocklist-only or nothing), "dirty systems" (one-time
   per-device binary scan into rules, then everything new must pass).
3. The portable-app-specific control = block execution from user-writable locations
   (Downloads, %USERPROFILE%, USB). AppLocker default rules allow only Windows +
   Program Files -> implicit deny elsewhere the moment the EXE collection is enforced.
   Community threads confirm this is the standard answer (r/Intune: "AppLocker is a bit
   easier to configure" for Downloads/USB; r/sysadmin: AppLocker deny-all + allowlist
   of Program Files/Windows; Spiceworks Aug 2025: SRP or AppLocker blocking
   user-accessible paths incl. USB).
4. AppLocker rules match ALL PE files regardless of extension (renaming exe->txt does
   not dodge it). MS Learn working-with-applocker-rules.

## Options menu (per-option sources)

A. WDAC / App Control for Business — kernel-level default-deny allowlist. Rule types:
   signer/publisher, hash, path, ISG reputation, managed installer, process. Multiple +
   supplemental policies for team exceptions. Deny-only policies MUST include AllowAll
   rules or they block everything. Audit mode: watch 3076 events. MS recommends
   signer/file-attribute rules over hash rules (hash churn). 5 MS Learn pages, all
   current Mar 2026.
B. AppLocker — user-mode, per-user/group rules (WDAC cannot do per-user), publisher/
   path/hash conditions; MS explicitly recommends pairing with WDAC on shared devices.
   Maintenance mode (no new features).
C. EPM governance layer (provenance/trusted-ownership pattern; 3 vendors, independent):
   - CyberArk EPM article 000050743 "EPM - How to Contain User-Based Applications"
     (Apr 2026) — now tagged "Idira Endpoint Privilege Manager (EPM)". Defines
     user-based apps = installer-based or portable in %USERPROFILE%; names Agentic AI
     (Claude, Cursor) as the growing driver. 3 layers: (1) risk-reduction — restrict
     ALL user-based apps from sensitive OS components; (2) allowlist — Location
     (%USERPROFILE% incl. subfolders) + Publisher + Original Filename + Checksum, with
     checksum as THE matcher for unsigned files (metadata/filenames in user profiles
     can be altered); (3) discovery/log, then higher-priority default-deny.
   - Ivanti App Control: Trusted Path policies — allow exes in designated (ideally
     shared, protected) paths, optionally limited to a file owner attribute; dev/test
     churn use case.
   - ThreatLocker: Default-Deny policy + Secured Mode; Learning Mode catalogs executed/
     installed files into applications. GOTCHA: files in Documents/Downloads/Desktop/
     Users are NOT auto-profiled during automatic learning unless matchable to an app
     name — portable apps in user dirs don't silently auto-allow. Unsigned files:
     combine path+process+created-by, never a single parameter. Don't permit Microsoft
     certificates broadly (signs too much).
D. Reputation-based — ISG / Smart App Control ("trust apps with good reputation").
   Soft option; orgs with org-approved-set compliance (Essential Eight ML2+) drop it.
E. Convert-and-manage — take legit portable apps and make them managed instead of
   blocking: Intune Win32 packaging, signed catalog files, winget portable packages
   (winget-cli spec #182: portable/standalone apps are first-class packages, installed
   under user local app data). Single-source in this run (the spec itself).
F. macOS Santa — MONITOR (log) / LOCKDOWN (deny unknown) / Standalone (unknown exec
   held until user approves via TouchID/password, auto-creates local SigningID or
   SHA-256 rule). Rule precedence: CDHash -> Binary -> SigningID -> Cert -> TeamID.
   Path regex exists but explicitly discouraged (trivially bypassable). BlockUSBMount
   built in. Not covered: scripts, dlopen, DYLD_INSERT_LIBRARIES. google/santa repo
   ARCHIVED (2025) -> maintained fork github.com/northpolesec/santa; docs santa.dev.
   Google's rollout playbook (Upvote): monitor -> allowlist most-used certs ->
   progressive lockdown groups.

## Gotchas (multi-source)
- Hash rules rot on every update (MS + ThreatLocker).
- Publisher-only allow = too broad (ThreatLocker: even ransomware can be signed).
- Path rules in user-writable dirs are the weak point of every tool: WDAC refuses
  user-writable FilePath rules by design; Santa docs discourage path regex; Upvote
  warns it lets users circumvent lockdown.
- Dirty-systems problem: allowlisting onto existing fleets breaks un-scanned apps
  (MS per-device scan approach; EPM learning modes exist for this).
- Deny-only policies must include AllowAll rules or you block everything (MS).

## Tooling notes (verified this run)
- Firecrawl refuses Reddit ("we do not support this site") — capture Reddit threads via
  firecrawl_search result snippets (title/description) and disclose snippet-level
  evidence in the deliverable.
- Firecrawl formats:["query"] LLM extraction returns thin/unreliable answers on large
  reference pages — request formats:["markdown"] instead; very large pages truncate
  (~150K chars), accept head+tail or re-scrape with a targeted query.
- MS Learn URLs drift: old "microsoft-recommended-block-rules" 404s; current =
  .../app-control-for-business/design/applications-that-can-bypass-appcontrol. On 404,
  re-search for the canonical URL rather than guessing the path.

## Key URLs
- https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/appcontrol-and-applocker-overview
- https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/design/common-appcontrol-use-cases
- https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/design/understand-appcontrol-policy-design-decisions
- https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/design/applications-that-can-bypass-appcontrol
- https://community.cyberark.com/s/article/EPM-How-to-Contain-User-Based-Applications
- https://help.ivanti.com/ht/help/en_US/IES/86/UG_AC/work-with-trusted-path.htm
- https://threatlocker.kb.help/maintenance-modes/ (+ creating-custom-rules)
- https://cas8.docs.cisecurity.org/en/latest/source/Controls2/ (CIS Control 2)
- https://santa.dev/ | https://github.com/google/santa | https://northpole.security/docs/santa/features/binary-authorization
- https://github.com/microsoft/winget-cli/blob/master/doc/specs/%23182%20-%20Support%20for%20installation%20of%20portable%20standalone%20apps.md


## Reference: wdac-applocker-implementation.md

# WDAC + AppLocker Implementation Reference

## WDAC Policy Architecture (Multi-Policy Format)

### Base Policy (DefaultWindows, signed)

```xml
<?xml version="1.0" encoding="utf-8"?>
<SiPolicy>
  <VersionEx>10.0.0.0</VersionEx>
  <PolicyTypeID>{A2452718-F099-4B13-B11E-853E51130F2C}</PolicyTypeID>
  <PolicyID>{YOUR-POLICY-GUID}</PolicyID>
  <BasePolicyID>{YOUR-POLICY-GUID}</BasePolicyID>
  <Rules>
    <Rule><Option>Enabled:Unsigned System Integrity Policy</Option></Rule>
    <Rule><Option>Enabled:Audit Mode</Option></Rule>
    <Rule><Option>Enabled:Managed Installer</Option></Rule>
    <Rule><Option>Enabled:ISG</Option></Rule>
  </Rules>
  <Signers>
    <Signer ID="Microsoft" Name="Microsoft">
      <CertPublisher Value="Microsoft Corporation" />
    </Signer>
    <Signer ID="Google" Name="Google">
      <CertPublisher Value="Google LLC" />
    </Signer>
  </Signers>
</SiPolicy>
```

### Deployment via Intune (ApplicationControl CSP)

```
Endpoint Security > App Control for Business > App Control for Business tab
> Create Policy
> Configuration settings: Enter xml data
> Upload: {PolicyGUID}.cip (renamed to .bin)
> OMA-URI: ./Vendor/MSFT/ApplicationControl/Policies/{GUID}/Policy
> Data type: Base64 (file)
```

Use ApplicationControl CSP (not AppLocker CSP) — supports multi-policy, rebootless. 350KB limit.

### Managed Installer Setup

**Step 1:** Endpoint Security > App Control for Business > Managed Installer tab > Create

**Step 2:** AppLocker policy via PowerShell (AppLocker CSP doesn't support ManagedInstaller rule collection):
```powershell
Set-AppLockerPolicy -XMLPolicy $PolicyXML -Merge
appidtel.exe start -m
```

**Step 3:** Verify:
```powershell
Get-AppLockerPolicy -Effective -XML
Test-Path "C:\Windows\System32\AppLocker\ManagedInstaller.AppLocker"
```

### AppLocker Per-User Rules (Shared Workstations)

AppLocker is the ONLY tool with per-user/group rules. Deploy via Intune PowerShell script (not OMA-URI).

Publisher rules match BEFORE path deny rules — signed apps from approved publishers allowed even in user-writable locations.

## Key Gotchas

1. Signed base policies require reboot on Win11 <24H2 with HVCI (deploy via script)
2. Autopilot + WDAC + CLM conflict (error 0x800705b4) — defer policies 24+ hours post-enrollment
3. PowerShell CLM breaks many scripts — deploy separately from binary enforcement
4. 350KB OMA-URI limit — use signer rules + managed installer
5. Deny rules in supplemental policies are silently ignored
6. Add-SignerRule resets HvciOptions to 0 — always run Set-HVCIOptions after
7. Supplemental signer rules go on BASE policy, not supplemental
8. Empty deployed policy = nothing runs (including Windows)
9. FilePath rules require admin-write-only paths

## Event IDs

| ID | Log | Meaning |
|---|---|---|
| 3076 | CodeIntegrity > Operational | Audit violation |
| 3077 | CodeIntegrity > Operational | Enforcement block |
| 8003 | AppLocker > EXE and DLL | Audit (would block) |
| 8004 | AppLocker > EXE and DLL | Enforcement (blocked) |

Enable: `wevtutil sl "Microsoft-Windows-CodeIntegrity/Operational" /e:true`

## Commands

```powershell
# Convert XML to binary
$PolicyID = ([xml](Get-Content .\Policy.xml)).SiPolicy.PolicyID
ConvertFrom-CIPolicy -XmlFilePath .\Policy.xml -BinaryFilePath ".\$PolicyID.cip"

# Merge supplemental
Merge-CIPolicy -PolicyPaths .\Base.xml,.\Supplemental.xml -OutputFilePath .\Merged.xml

# Enable managed installer
Set-RuleOption -FilePath .\Policy.xml -Option 13

# Check HVCI
Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard
```
