---
name: mde-advanced-hunting
description: Write, audit, and fix Microsoft Defender Advanced Hunting (MDE AH) KQL queries and the PowerShell pipelines that consume their CSV exports. Schema gotchas (parse_path, bool cert columns, FileProfile collisions), join semantics, and producer/consumer contract testing.
tags: [kql, microsoft-defender, security, hunting, windows]
triggers:
  - Microsoft Defender advanced hunting query
  - KQL hunting in Defender
  - investigating device events or alerts

---

# MDE Advanced Hunting (KQL + downstream pipelines)

## When to use
- Writing or auditing MDE AH queries (file provenance, process/execution hunting, persistence, DLL sideloading, shadow-IT/portable-app discovery)
- Building PowerShell scoring/enrichment scripts that consume AH CSV exports
- Debugging queries that error, return nothing, or silently miss data

## Verified schema & semantics pitfalls (checked against MS Learn + runtime behavior)
- `parse_path()` returns property **`Filename`** (capital F), not `FileName`. `parse_path(x).FileName` is always null -> `where isnotempty(...)` filters everything -> step silently dead. Classic silent-kill bug.
- **`has` is TERM-based — the silent-dead-filter bug (biggest find of the portable-app audit).** Terms are maximal alphanumeric sequences (MS: datatypes-string-operators; `"KustoExplorerQueryRun" has "Explorer"` → false). Any RHS containing dots/backslashes/slashes/spaces/hyphens can never be a term, so `has "foo.exe"`, `has @"AppData\Local\"`, `has "\CurrentVersion\Run"`, `has "/create"`, `has_any (["C:\Tools\", ...])`, and `on $left.A has $right.FileName` NEVER match — the query runs, filters silently never fire (this made ALL persistence detection + AppData/Temp discovery dead in a production query). Fixes: `contains` for path substrings; whole-filename joins via `tostring(parse_path(X).Filename)` + `==` equality (also more precise). **HYPHENS COUNT TOO (round 17): `has "Register-ScheduledTask"` / `has "Set-ScheduledTask"` NEVER matched — the PowerShell task-persistence leg was silently dead from v3.1 to v3.18 despite a round-6 self-audit that called it "clean" (it checked whole-word-ness, not hyphenation). When re-auditing `has` uses, check for ANY non-alphanumeric in the RHS, not just dots/slashes.** WARNING: `contains_any` does NOT exist in Kusto (verified against the full datatypes-string-operators table, kql-quick-reference, and the kusto/query docs map — the `_any` family is `has_any`/`has_all` only; a query using it ERRORS at that step). For multi-pattern substring matching use an or-chain of `contains`, or `matches regex` with an alternation (`@\"(?i)alt1\\\\|alt2\"` — prefix `(?i)` for case-insensitivity, double the backslashes for literal `\\`), or `has_any` only when every RHS is a plain word. Whole words ("Downloads", "Register-ScheduledTask" is NOT one — hyphen) are safe with `has`. Audit any existing query for `has` + punctuation AND for `contains_any`.
- SmartScreen ActionTypes in `DeviceEvents`: `SmartScreenAppWarning`, `SmartScreenUserOverride` (verified in microsoft/Microsoft-365-Defender-Hunting-Queries); `SmartScreenUrlWarning`/`SmartScreenExploitWarning` also exist. `Experience` lives in `AdditionalFields` JSON.
- Kusto `join ... on Key` requires Key on BOTH sides. A `summarize X = agg() by NewName = OldCol` renames the column; if that column was the join key, the whole query ERRORS at that step. Fix: summarize `by Key = <correct source col>`.
- Same-named non-key columns on both join sides: right side gets "1" appended (SHA1 -> SHA11). Join-key columns are NOT renamed. Always check which `SHA1` you're referencing after a join.
- `DeviceFileCertificateInfo`: `IsSigned` / `IsTrusted` are **bool** (True/False), not "Signed"/"Unsigned" strings. Compare with BOOL LITERALS — `IsSigned != true or isnull(IsSigned)` — the documented/community idiom (df00tech, MS queries). Don't rely on string coercion (`!= "True"`); it's unverified and the string never appears in the data.
- DeviceFileCertificateInfo only has rows for files with cert telemetry; `IsSigned` is ~always true. The useful discriminators: `IsTrusted` and ROW ABSENCE (absent = unsigned/no telemetry).
- `summarize arg_max(Timestamp, *) by SHA1` across all devices lets ONE device with a broken trust chain poison the verdict. Prefer `make_set(tostring(IsTrusted))` consolidation -> True/False/"Mixed".
- `DeviceRegistryEvents` hive coverage — CLAIM REVERSED (v3.6, external-audit pass 3): an earlier HKLM-only claim (from one MS Q&A) is contradicted by community runbooks that query HKCU paths in this table directly — Crimson7research runbook filters `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`, forenza.io COM-hijack hunts query per-user CLSID hives. Treat both hives as covered; a `contains @"\CurrentVersion\Run"` filter matches either. The MS Q&A case likely reflects events not emitted in that specific configuration, not a schema limit. Never state "HKLM only" without re-checking community usage.
- `mv-expand` on an empty array drops the row; `mv-expand A, B` is a cartesian product. Guard empties before expanding.
- Kusto `in` does NOT accept subqueries — use a join (or a let variable holding a scalar list).
- `set_has_element(arr, "false")` works for string sets; values from `tostring(bool)` are lowercase "true"/"false".
- KQL verbatim strings `@"..."`: backslash is literal, `""` escapes a quote. When reading file content through JSON (read_file), every `\\` in the JSON is ONE backslash in the file — count escapes carefully before declaring a pattern broken.
- Persistence via `Register-ScheduledTask` (PowerShell) bypasses schtasks.exe filters — add a second join scoped to powershell.exe/pwsh.exe + "Register-ScheduledTask" in the command line, extracting the `-Execute` value.
- TVM inventory `SoftwareName` carries versions ("7-Zip 21.07 (x64)") — name equality with a short filename never matches. Join on `SoftwareVendor` presence instead (vendor-known); this also lets you delete dead ShortName machinery.

- SUMMARIZE CONSTANT-AGGREGATE = RUNTIME SEMANTIC ERROR (round 17, first real portal run): `| summarize Flag = "True" by SHA1 = X` parses clean, survives every static audit, and DIES at run time — "summarize must have at least one aggregate function". provenance-full.kql carried FIVE of these (PersistenceDetected ×3, PersistenceTask, PersistenceTaskPS) through 16 audit rounds; only the portal/API run caught it. Existence-flag idiom that preserves the output contract: `Flag = take_any("True")` (take_any accepts a constant expr — MS Learn; returns "True" for any matched group, null otherwise, so downstream `iff(isempty(...))` logic is untouched). Bare-column "aggregates" (`| summarize DeviceCount by X`) are equally invalid. When a first-ever portal run errors, scan EVERY summarize for a constant/bare-column aggregate, not just the flagged line — the engine stops at the first failure.
- UNDEFINED SCALAR IN iff — RUNTIME-ONLY ERROR CLASS #2 (round 18, second real run): the RMM detection block referenced `LowerCompany` but that block extends `LowerRmmCompany` — "failed to resolve scalar expression named lowerCompany", in BOTH branches (the two-branch drift class again). Parses clean, survives static audits, dies at run. The AI-tool block's `LowerCompany` is LEGITIMATELY scoped (extended 2 lines above its use), so a blanket find/replace of the bare column name would BREAK the AI block (LowerRmmCompany is project-away'd by then → a NEW resolve error). When a first-run error names a scalar: diff every case-folded identifier (Lower*, *Lower, tolower aliases) against its extend site within the SAME operator chain, then check both branches. Safe user-side fix recipe: find/replace the unique quoted-name tokens (anydesk/teamviewer/splashtop/logmein/realvnc/gotomypc/connectwise), never the bare column.
- KS204-ON-EVERY-LET triage: editor underlines "name doesn't refer to any known column, table, or data function" on ALL let names (including mid-file ones like TvmVendors/ProvenanceCandidates) mean either (a) the editor text isn't the full query — check the FIRST and LAST lines, not the middle (a paste can truncate mid-file and still look right at both ends), or (b) an ANALYZER-ONLY glitch: this query's ═ box-drawing banner comment lines + em-dash made the portal IntelliSense flag every let while the engine ran the exact same text fine. Press Run before debugging squiggles; a real engine error (e.g. the summarize one above) is the only trustworthy signal.
- AH API 2026+: legacy `api.security.microsoft.com/api/advancedhunting/run` (AdvancedHunting.Read.All) is mid-retirement — dead Feb 2027. Current path: Graph v1.0 `POST https://graph.microsoft.com/v1.0/security/runHuntingQuery`, permission `ThreatHunting.Read.All` (delegated + application), body `{"Query": "..."}` (+ optional `Timespan`), response properties are LOWERCASE `schema`/`results` (unlike the legacy `Schema`/`Results`), 100k-row cap and 50MB result cap (hit → truncated; warn at 100000), 30-day data window, ~45 calls/min tenant quota, 3-min request timeout.

## FileProfile enrichment
- Syntax: `| invoke FileProfile(SHA1, 1000)` — x = file ID column (SHA1/SHA256/InitiatingProcessSHA1...), y = limit 1-1000, **default 100** if omitted. Use the 2-arg form.
- FileProfile returns Signer, Issuer, IsRootSignerMicrosoft, SoftwareName — which COLLIDE with cert-join columns. `project-away` them before invoking or the query errors on duplicate columns.
- `ProfileAvailability`: Available / Missing / Error / empty (empty = past the file cap). Downstream scripts must fall back to the cert branch when not "Available".
- Cap ~1000 files/query — enrichment only; never a hard filter.

## Portable-app discovery domain lessons
- Sideload detection must be flag-only or +1, never +3: portable apps legitimately ship unsigned DLLs in their own folder (7-Zip's 7z.dll is unsigned next to unsigned 7z.exe) — the packaging pattern IS sideloading. +3 floods the risky queue with every legit portable tool.
- SCORING PHILOSOPHY (v3.3, user-driven — "are we overfitting? should we just drop risk entirely?"): weighted 0-10 composites (Portability AND Risk) were DROPPED from this pipeline. Without labeled data, weights overfit the analyst's intuition one complaint at a time (sideload +3→+1 after 7-Zip, TVM join rebuilt after it never matched, signed+prevalent shadow IT scoring 0 while being exactly what you want to see). A composite also lies by omission: Risk 0 reads as "reviewed" when it means "unjudged". Replacement: raw facts + boolean flags + ONE unweighted RedFlagCount (tally of independent red-flag booleans — sortable, nothing to argue with) + recency buckets (RedFlagged ≥2 / Internal / New / Installer / Stable) + the existing Decision carry-over (that + Growth KPI were doing the real work all along). Do NOT propose re-adding composite scores to this toolchain.
- v3.2 fact columns (KQL-side; PS1 just carries them): PathCategory (case() — order matters: Temp before AppDataLocal*, AppDataLocalPrograms before AppDataLocal, Downloads/Desktop before UserHome), launcher countifs Script/System/Explorer/Installer counted on InitiatingProcessFileName (that IS the launcher; InitiatingProcessParentFileName is the GRANDPARENT — a classic MDE naming trap), IsInstaller (name regex setup|install|update|patch|repair OR InstallerLaunches>0), IsInternalTool (Signer/CompanyName matches the InternalPublishers regex let — fill per org), UNC share execution via `FolderPath startswith @"\\"` (previously completely invisible).
- Installers: classify, never silently filter by name — the removed `!contains "setup"/"install"` KQL exclusion was hiding malicious setup.exe; classification (IsInstaller bucket) + the census's ≥2 distinct-day gate handle the one-off install flood.
- Internal tools: unsigned + fleet-narrow footprint are EXPECTED state — flags stay (INTERNAL_UNSIGNED is the "should be signed" governance finding) but UNSIGNED/LOW_PREVALENCE don't count toward RedFlagCount and internal tools don't bucket RedFlagged.
- SIGNED_PREVALENT flag: signed + gp≥10000 + zero red flags = "looks fine, isn't governed" — makes signed shadow IT (mouseclicker.exe) surface instead of zeroing out.
- NON-LYING READABILITY LAYER (v3.1, user-driven — "can we score in a way that doesn't lie but reads easier?"): YES, if the score is an INVERTIBLE FUNCTION OF DISPLAYED FACTS — every point maps 1:1 to a visible flag and there's no arithmetic the reader can't redo. What lies: hidden weights, caps/floors, 0-10 scales. What doesn't: (1) **Families vector** — group the red flags into Trust/Behavior/Context; emit "T2 B6 C1"; it's a PARTITION of RedFlagCount so T+B+C==rf by construction (assert this invariant in tests — one patch dropped a `$c++` and silently broke it). (2) **LoudSignal** — ONE qualitative tier, a documented flag list (MALWARE_HIT, ALERT_HIT, PERSISTENCE, RENAMED_LOLBIN, ENCODED_CMD, DOWNLOAD_CRADLE, ASR_VERDICT [renamed v3.6 from ASR_UNTRUSTED when the ASR join grew to 4 rule families], WMI_PERSISTENCE, STARTUP_LNK); category, not weight; Loud bucket outranks RedFlagged — one threat-shaped signal beats three context flags, matching real triage. (3) **Profile string** — "Unsigned | Rare | New": trust state (Signed/Untrusted/Unsigned), prevalence band (Rare<1k/Common<100k/Prevalent), age band (New<30d/Established), "?" when the signal is unavailable — the same prevalence/age/trust triad Microsoft's ASR untrusted-executable rule uses, as categorical facts.
- INSTALLER CLASSIFICATION BY BEHAVIOR (v3.3): renamed installers ("Un_A.exe", "wps_office_64.exe") defeat the name regex — detect what installers DO: (1) writes to `\Uninstall\` registry keys (definitive installed-software marker; HKLM only — AH has no HKCU registry telemetry, so user-level installs still slip: documented limitation), (2) spawns msiexec.exe/wusa.exe CHILDREN (bootstrapper pattern; complement of InstallerLaunches which counts msiexec as PARENT), (3) FilesCreated >= 5 AND DistinctDays <= 3 (file-creation volume × near-once execution — the DistinctDays guard keeps daily-run portable suite launchers out of the installer bucket). Implemented as SHA1-scoped joins on the candidate set, same pattern as the persistence steps. SAFETY PROPERTY: the label only affects the BUCKET, never visibility, and RedFlagged outranks Installer — a malicious renamed installer can never hide behind the label; false positives cost one review. FilesCreated survives as a fact column.
- PATH COVERAGE CHECKLIST (v3.5, extended v3.9): the discovery filter is now `FolderPath contains @"\Users\"` + `@"\ProgramData\"` + Windows\Temp + `^[D-Z]:\` (USB) + ExtraPortableRoots + UNC (`startswith @"\\"`). The \Users\ catch-all SUBSOMES Downloads/Desktop/AppData/Public and — critically — admits per-user tool folders the specific patterns missed: scoop (`\scoop\`), PortableApps (`\PortableApps\`), OneDrive-synced tools, custom user dirs. ProgramData (v3.9) is NOT under \Users\ and was completely invisible until added — yet it holds Chocolatey shims (`C:\ProgramData\chocolatey\bin`, official choco docs) and is a repeatedly documented malware-staging dir (Emotet random-named DLLs, Black Basta's red-flag list, the DFIR Report staging analysis). PathCategory order: Chocolatey (`\chocolatey\` → "Choco" → CHOCO_MANAGED) BEFORE the generic `\ProgramData\` → "ProgramData" → PROGRAMDATA_STAGING; Scoop → SCOOP_MANAGED, PortableAppsFolder → PORTABLEAPPS (flag-only). Same ProgramData addition in the sideload DLL filter. Pre-window files in unmapped fixed locations remain structurally invisible (retention + filter bounds).
- AV/PUA VERDICTS (v3.10): Defender AV engine verdicts are a distinct signal layer from alerts (AlertEvidence) and cloud reputation (FileProfile ThreatName) — `AntivirusDetection` and `AntivirusMalwareBlocked` in DeviceEvents; the ActionType descriptions explicitly cover "malware, potentially unwanted applications or suspicious behavior", i.e. the gray-tool layer (hacktools/keygens/activation tools) that gets engine flags without ever rising to alert status — exactly the portable-discovery profile. Recipe: materialized `let AvDetections = materialize(( DeviceEvents | where ActionType in ("AntivirusDetection", "AntivirusMalwareBlocked") | where isnotempty(SHA1) | summarize AvDetections = count() by SHA1 ));`, join in BOTH branches (no knob — AV is always on), PS1 AV_FLAGGED red flag +1, Trust family, NOT loud (real malware already hits the louder MALWARE_HIT/ALERT_HIT paths). Verified: PUA-flagged unsigned keygen → rf=2 RedFlagged; clean signed+prevalent → rf=0 Stable.
- RMM / REMOTE ACCESS TOOLS (T1219) are a FIRST-CLASS governance category, not a generic portable app: rogue portable AnyDesk/TeamViewer/RustDesk is a top-tier finding (Bert-JanP's RMM research note, Splunk's RMM analytic). Classify like the AI-tool list: `IsRmmTool` from name+company contains-chains (anydesk, teamviewer, rustdesk, screenconnect, connectwise, splashtop, ammyy, dwservice, parsec, gotomypc, logmein, VNC family, tacticalrmm, supremo, zohoassist, chromeremote...). RMM_TOOL is a RED flag (+1) — the v3.5 test showed a signed+prevalent AnyDesk would otherwise sink to rf=0, and a portable RMM tool is review-worthy by definition.
- REMOTE-LAUNCH CONTEXT: ASR rule d1e49aac ("Block process creations originating from PsExec and WMI") emits `AsrPsexecWmiChildProcessAudited/Blocked` — a portable app CREATED via psexec/WMI is the lateral-movement-flavored launch context. Separate join, separate column (RemoteLaunchHits), same UseAsrSignals knob; PS1 flag REMOTE_LAUNCHED is flag-only (legit remote admin exists).
- SIDELOAD SUBDIRECTORY EVASION: same-folder DLL checks (`parse_path(FolderPath).DirectoryPath == parse_path(TopFolderPath).DirectoryPath`) miss DLLs in SUBDIRECTORIES of the exe's folder — Elastic's own rule tuning fixed exactly this (endswith→startswith directory matching). Relax to same-folder-or-subdirectory; keep flag-only.
- RAW-IP CALLBACKS (v3.7, CORRECTED v3.15): DNS-less outbound connections are the classic unmanaged-app/C2 pattern and the network join was blind to them. Recipe: `RawIpConnections = countif(isempty(RemoteUrl) and isnotempty(RemoteIP) and RemoteIPType == "Public")` in the DeviceNetworkEvents summarize. CORRECTION: the original used `RemoteIPIsPrivate == 0` — THAT COLUMN DOES NOT EXIST (audit round 14: absent from MS Learn schema AND the xdrinternals in-portal mirror; a Reddit r/DefenderATP analyst derives it via `extend RemoteIPIsPrivate = iff(ipv4_is_private(RemoteIP), ...)`, i.e. it's a computed expression, not schema). The real column is `RemoteIPType` (documented values: Public/Private/Reserved/Loopback/Teredo/FourToSixMapping/Broadcast). Lesson: a "verified in the schema" claim from a prior round is still challengeable — re-check against BOTH MS Learn and the portal mirror.
- ACTOR-BEHAVIOR EVENTS (v3.11) — the candidate DID something; JOIN ON `InitiatingProcessSHA1`, NOT the event's `SHA1` (for SensitiveFileRead/tampering APIs the event's own SHA1 is the TARGET file/process — joining on it never matches candidates). One materialized `ActorBehaviorEvents` let covers: `SensitiveFileRead` (ssh keys/mail archives — credential access; SENSITIVE_READ red+loud), `OpenProcessApiCall`/`ReadProcessMemoryApiCall`/`WriteToLsassProcessMemory`/`ProcessPrimaryTokenModified` (injection primitives; TAMPERING_APIS red, not loud — debuggers/anti-cheat legitimately do some), `FileTimestampModificationEvent` (timestomping T1070.006; TIMESTOMP flag-only — extractors/backups restore timestamps), `ShellLinkCreateFileEvent` (LNK created by candidate — MS Learn Q&A validates; SHELL_LINK_CREATION flag-only; installers creating shortcuts is normal, a non-installer doing it is odd), `DpapiAccessed` (T1555.004 DPAPI-secret decryption; DPAPI_ACCESS red+loud). Verified regression: sensitive-reader → Loud rf=2; tampering tool → RedFlagged rf=2; timestamper → Stable rf=1 with TIMESTOMP.
- SELF-DELETION (T1070.004, v3.13): candidate deleted a file with its own name — AcidPour/RansomHub/ProLock pattern; MITRE's documented detection strategy is literally "processes that delete their own executable". Recipe: DeviceFileEvents `FileDeleted` joined to candidates on InitiatingProcessSHA1, then `where FileName == FileName1` (post-join disambiguation: left FileName = deleted file, right FileName1 = candidate name). SELF_DELETED red+loud. Scope to the radar branch only — scoping needs the branch-1 candidate set; branch-2 scoping would be circular (same constraint as installer-behavior joins).
- NAME-BASED DISCOVERY + MASQUERADE (v3.12 + v3.8/13 PS1): (1) PortableApps.com-format launchers — the official Format spec names the launcher `*Portable.exe` and apps "run in local mode from anywhere", so a C:\-root FirefoxPortable.exe is invisible to path filters; add `FileName endswith "Portable.exe"` to the discovery filter + a PortableLauncher PathCategory (PORTABLE_LAUNCHER flag). (2) SYSTEM_NAMED (PS1): a COPIED system binary keeps its OriginalFileName, so RENAMED_LOLBIN never fires — a system-name-in-user-path IS the signal (techjack's hunting set: svchost/csrss/lsass/services/smss outside System32). red+loud. (3) SEARCH_ORDER_HIJACK (PS1): a SYSTEM-named DLL (version.dll/winmm.dll/ws2_32.dll/bcrypt.dll/amsi.dll... ~28-name list) in the candidate's folder = T1574.001 preloading trick — check the SideloadedUnsignedDlls values PS1-side; red, not loud (some legit apps ship d3d9-style shims). (4) DOUBLE_EXTENSION (PS1): `invoice.pdf.exe` lures with SPOOFED OriginalFileName defeat RENAMED entirely — regex `^.+\.(docx?|xlsx?|pptx?|pdf|jpg|jpeg|png|gif|zip|rar|7z|txt|mp3|mp4|iso|lnk|scr|bat|cmd|vbs|js)\.exe$`; flag-only; the explicit extension list prevents 7zsetup-x64.exe-style false positives (verified).
- VERIFY FACT COLUMNS ARE CONSUMED: the ELEVATED lesson generalizes — each audit pass, diff the output columns against the flags that read them. Collected-but-never-consumed columns are latent signals (ProcessIntegrityLevel sat unused for versions before ELEVATED).
- ELEVATED (v3.7): ProcessIntegrityLevel "High"/"System" → red flag, Behavior, not loud. Lesson: audit your fact columns for signals you collect but never consume — this one had been sitting in the output for versions. An unsigned+elevated app becomes rf=2 RedFlagged; a signed+elevated tool stays rf=1 Stable with ELEVATED as context (verified).
- DEVICEFILEEVENTS ACTION TYPES VERIFIED (v3.7): exactly FileCreated / FileDeleted / FileModified / FileRenamed — nothing else. `FileCreated` filters are safe; there is no FileCreatedRemotely.
- INITIATOR-CLASS MAP (v3.8) — the "how did the file arrive" classification used to decide user-introduced vs Other: validate it against real arrival vectors, don't trust memory. Microsoft's own suggested "Downloads" query validates the approach (`InitiatingProcessFileName =~ "firefox.exe"` style). Found in this pipeline: `onedrive.exe` was misclassified as ChatApp (it's a cloud-sync client), and whole vectors were missing — cloud-sync (dropbox, googledrivesync/googledrivefs, megasync, pcloud, boxsync, syncthing, rclone), download managers (idman, fdm, aria2c, jdownloader, xdman, eagleget, nettransport, orbitdm, freedownloadmanager), torrent clients (qbittorrent, utorrent, bittorrent, transmission, deluge, vuze, tixati), WPS/LibreOffice (macro-capable docs → OfficeMacro class), vivaldi/palemoon/waterfox, mailbird/emclient/foxmail, wechat/line/viber/element. Files arriving via a missing class fell to "Other" → the arrivals radar missed them ENTIRELY (classify as: Browser/Email/ChatApp/CloudSync/DownloadManager/Torrent/Archive/OfficeMacro/ScriptHost/Explorer, "Other" excluded). PS1 context flags: CLOUD_SYNCED, DM_DROP, TORRENT_DROP (flag-only).
- MATERIALIZE REUSED LETS (v3.8): in a multi-branch query, a let referenced by BOTH branches is computed TWICE per run. Wrap the small summarized lets in `materialize(( ... ))` (syntax: `let X = materialize(( DeviceEvents | ... ));`) so each is computed once — verified against MS docs: 5GB cache cap per cluster node, and exceeding it ABORTS the query, so ONLY materialize small lets (summarized-by-key outputs); leave big raw scans (ExecutedFiles/UserContext) unmaterialized and document why. Docs require benchmarking before use.
- TLD ORIGIN FLAGS REJECTED (v3.8): sketchy-TLD analysis of FileOriginUrl was considered and rejected — no community precedent in MDE hunting, high noise potential; the review value didn't justify the false-positive load. Record rejections with reasons in the audit trail; not every idea survives contact with evidence.
- `matches regex` with a TRAILING BACKSLASH is a compile error (round 14): `@"^[D-Z]:\"` — one backslash before the closing quote — is RE2-invalid ("trailing backslash"; ClickHouse/RE2 evidence, posthog#58706; Kusto's regex page documents the RE2 family). The pattern must be `@"^[D-Z]:\\"` (verbatim string: two backslashes = regex `\\` = ONE literal backslash). Byte-count every verbatim regex when auditing: contains-patterns need 1 backslash per separator (`@"\Users\"`), startswith-UNC needs 2 total (`@"\\"`), regex-literal-backslash needs 2 per separator (`@"^[D-Z]:\\"`, `@"(?i)C:\\Tools\\"`).
- `invoke FileProfile(x, 1000)` ERRORS if the input already has ANY FileProfile output column — most commonly `Signer` from a prior DeviceFileCertificateInfo join (round 14: branch 2 of provenance-full.kql had this; FileProfile's documented output includes Signer/Issuer/IsRootSignerMicrosoft/SignatureState/SignatureType etc., and invoke appends the function schema to the input — duplicate names are impossible in a Kusto tabular schema and there is no rename mechanism, so it fails at that step). project-away the colliding columns first; if you need them after enrichment (IsInternalTool uses Signer), carry them under a fallback name (`| extend CertSigner = Signer | project-away Signer` … `isnotempty(Signer) or isnotempty(CertSigner)`). FileProfile's second parameter is a RECORD CAP (1-1000, default 100) — not a time window (MS Learn fileprofile-function; ProfileAvailability description mentions "the maximum number of files was reached").
- AFTER ANY JOIN whose right side carries a column that also exists on the left, a bare `by <name>` binds to the LEFT side — Kusto renames the right side's duplicate with a `1` suffix (`Key` → `Key1`, `FileName` → `FileName1`; join-inner docs example output `Key | Value1 | Key1 | Value2`). Four persistence legs of provenance-full.kql died silently to this (round 15): schtasks/Register-ScheduledTask grouped by schtasks.exe/powershell.exe's OWN hash, ScheduledTaskCreated by DeviceEvents.SHA1 (no file → null), SelfDeletes by the deleted file's hash. Fix pattern: rename the right side in the project (`CandidateSHA1 = SHA1, CandidateFileName = FileName`) and group `by SHA1 = CandidateSHA1`. Never write a bare `by` after a join without checking both sides' schemas.
- JOIN KEYS ARE CASE-SENSITIVE: the join on-clause documents only `==` (community workaround for case-insensitive joins: tolower both sides BEFORE the join; `=~` in the on-clause is NOT documented). String operators =~/in~/contains/startswith fold ASCII ONLY — for non-ASCII comparisons use tolower() (MS in-operator docs: "Case-insensitive operators are currently supported only for ASCII-text. For non-ASCII comparison, use the tolower() function"). Windows file/registry names are case-insensitive and PE CompanyName metadata is arbitrary-case, so vendor/filename joins must be case-folded (round 15 fixed Run-key, schtasks, self-delete, TvmVendors joins; registry value-name compares now =~/in~).
- FULL ACTION-TYPE INVENTORY IN ONE FETCH: xdrinternals.com deviceevents page is 140KB+ and truncates; mandikgoyal/M365D_table (GitHub README) carries ALL AH action types per table in one document — fetch it and diff against your query's usage to find missed types (round 16 found ScheduledTaskUpdated, TamperingAttempt, AsrVulnerableSignedDriver* this way). Before ADDING an actor-join for a new type, verify attribution: confirm the event actually carries InitiatingProcessSHA1 (community/MS queries projecting InitiatingProcessFileName from it = evidence). Types rejected for attribution reasons: RemoteWmiOperation (actor = local wmiprvse.exe), SecurityLogCleared, UserAccountCreated. Types rejected for noise: NamedPipeEvent, WriteProcessMemoryApiCall, CFA violations (Documents/Desktop are default-protected — legit apps FP), GetAsyncKeyStateApiCall.
- TASK-MODIFICATION PERSISTENCE (T1053.005 = create AND modify): cover ScheduledTaskUpdated + schtasks /change + Set-ScheduledTask alongside the create forms; ScheduledTaskEnabled/Disabled/Deleted are NOT persistence (removal; enable = no content evidence). Startup-folder filters should match the canonical "\Start Menu\Programs\Start" prefix (covers FOLDERID_Startup AND FOLDERID_CommonStartup per KNOWNFOLDERID) — a bare "\Startup\" matches any unrelated folder named Startup.
- SEMANTIC-SUBSTITUTION FOR leftanti: excluding "rows already covered by branch 1" can reference the CHEAP candidate set instead of the fully-enriched branch pipeline when every enrichment join is a row-preserving leftouter — row-set identical, avoids recomputing FileProfile invokes and 20 joins (round 16). Non-materialized lets referenced N times get recomputed N times (materialize() docs) — materialize small summarized lets regardless of the "double-reference" rule when the reference count is high and the result is bounded.
- `hint.shufflekey=<key>` must be a JOIN KEY (docs: "Use a join key..."); a hint naming a non-join column (e.g. SHA1 on a join keyed by TopFolderPath/EvidencePath where the right side lacks SHA1) is at best a dead hint and at worst a resolve error — remove it. Join hints never change results ("don't change the semantic of join"), so removing is always safe.
- Two-branch FileProfile drift class (round 14): branch 1 had the project-away-before-FileProfile pattern, branch 2 (added later) forgot it. When auditing a two-branch query, diff the enrichment ORDER per branch, not just the columns.
- SCRIPT-BASED TOOLS = KNOWN SEPARATE ARTIFACT (round-6 verification): .ps1/.bat/.vbs/.hta/.cmd portable tools have no SHA1 in process events — they can't join a hash-centric census; they need their own query (pattern: powershell.exe + `-File` + user-writable script path — Microsoft's own query-language tutorial uses exactly this shape). Canonical extension list for that artifact (SentinelOne Power Queries startup-drop detection): bat cmd dll hta jar js jse msi ps1 psd1 psm1 scr url vba vbe vbs wsf exe. Recorded in the query header so the reference survives.
- ASR AUDIT EVENTS = NATIVE TRUST VERDICTS: DeviceEvents action types `AsrUntrustedExecutableAudited/Blocked` (rule 01443614 — prevalence/age/trusted-list criterion) and `AsrUntrustedUsbProcessAudited/Blocked` (rule b2b3f03d — USB) are in the AH schema. If those ASR rules are deployed in Audit mode, MDE's CLOUD prevalence/trust verdict is already emitted per execution — a first-class signal (join on SHA1) that beats rebuilding GlobalPrevalence+IsSigned proxies by hand. Check tenant rule deployment before rebuilding what the platform may already emit; the ASR rules reference page lists the AH action type for every rule. v3.4: implemented in this pipeline behind the `UseAsrSignals` knob (assumes deployment; inert if not), feeding `AsrUntrustedHits` → ASR_VERDICT red flag (+1 RedFlagCount).
- OPTIONAL-ENRICHMENT KNOB PATTERN: gate an optional join source with a bool let — `let UseX = true;` then `| join kind=leftouter (XLet | where UseX) on Key` — when the knob is false the source filters to an EMPTY table and the leftouter pads nulls (inert, no error). Kusto has no tabular if/else; this is the idiom. Used here for the ASR audit events and the beta TVM evidence table (beta → flip the knob if the schema breaks).
- DEVICEEVENTS ACTIONTYPE INVENTORY (v3.6): MS Learn only describes the table's COLUMNS — the ActionType VALUES live in the in-portal schema reference. Community mirror with the full 223-type list: `xdrinternals.com/docs/microsoftxdr/devices/deviceevents/` (also mirrors the other AH tables). Verified highlights beyond the ASR family: `ServiceInstalled` (4697-gated), `WmiBindEventFilterToConsumer` (WMI event-subscription binding — audit-independent), `ProcessCreatedUsingWmiQuery` (WMI process creation — audit-independent; the remote-launch signal that works WITHOUT the d1e49aac ASR rule deployed), `AppControl*` (WDAC events — AppControlScriptAudited/Blocked covers untrusted SCRIPTS: dormant until user-mode WDAC policies exist, then a 6-line knob closes the script-tools gap via platform signals), `DriverLoad`. Firecrawl-scrape gotcha: xdrinternals serves pages as a JSON-ESCAPED string — double-parse (`json.loads(raw)["result"]` may itself be a string to parse again) before regexing. Detail bank: deviceevents-actiontypes.md.
- NATIVE INVENTORY vs CUSTOM CENSUS: TVM software inventory is registry/MSI-centric (evidence = RegistryPaths) — it does NOT cover portable apps, so a custom census is not redundant, and a vendor-match against DeviceTvmSoftwareInventory is a meaningful "unmanaged" proxy. `DeviceTvmSoftwareEvidenceBeta` (BETA — table name/columns may change on GA) has `DiskPaths` (dynamic): file-level evidence of where TVM detected software — enables a sharp "has TVM ever seen THIS exact file path" check, stronger than vendor matching. Not ingested into Sentinel.
- Inner join (creation + execution, same device, in-window) = "arrivals radar", not a census. Files that predate the window or arrived via USB/cross-device copy are structurally invisible. Complement with an execution-only sweep (no creation requirement, >=2 distinct days filter). MDE AH default retention is 30d — every discovery query is retention-bounded; say so explicitly.
- PREFERRED SHAPE (v3): merge radar + census into ONE query — two branch lets (ProvenanceConfirmed = inner join + full enrichment; ExecutionOnly = leftanti on branch 1 + lean enrichment) + `union` + `Confidence` column. Shared lets can't drift; parallel files do (the ExampleOriginUrl drift was a two-file bug). `union` default kind=outer pads missing columns with nulls — safe for different schemas; check same-name-different-type columns (suffixed `_type`). FileProfile invoked PER BRANCH so the big branch can't starve the small branch's 1000-file cap.
- Persistence coverage (v3.6, verified against the full DeviceEvents ActionType inventory — was "Run keys + schtasks only"): Run keys (both hives) + schtasks CLI + Register-ScheduledTask + SERVICES (`ServiceInstalled` — event 4697, requires the "Audit Security System Extension" audit setting; inert without it) + WMI event subscriptions (`WmiBindEventFilterToConsumer` — audit-independent) + startup-folder LNKs (DeviceFileEvents FileCreated with `FolderPath contains @\"\\Startup\\\"`, InitiatingProcessSHA1 = candidate). v3.13/v3.14 additions: a registry-persistence leg for `AppInit_DLLs` (T1546.010 — official analytic exists), `Image File Execution Options` Debugger (T1546.012), `Winlogon` Shell/Userinit (T1547.004 — Cofense persistence reference), and service `ImagePath` writes under `\CurrentControlSet\Services\` (T1543.003 — audit-INDEPENDENT service creation, unlike the 4697-gated ServiceInstalled; detect.fyi service-hunting research validates the key path); plus the NATIVE `ScheduledTaskCreated` DeviceEvents event (method-independent — catches COM/.NET TaskService creation that schtasks-CLI command-line parsing misses). The actor joins use InitiatingProcessSHA1 (candidate DID the write), the run-key leg parses RegistryValueData. Only COM hijacks remain unqueryable. DOCUMENTED DEAD-END: Defender-exclusion tampering via the GPO path (`HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Exclusions`) is NOT collected in AH at all (cloudbrothers research — "you will not find any changes... in the advanced hunting data"); don't build tampering joins on it. PS1 flag semantics: SERVICE_INSTALLED = red, Behavior, deliberately NOT loud (a signed portable DB server installing a service stays Stable — verified); WMI_PERSISTENCE = red, loud; STARTUP_LNK = red, loud. ASR flag renamed ASR_UNTRUSTED → ASR_VERDICT once the join covered 4 rule families (untrusted-executable 01443614, USB b2b3f03d, abused-system-tool 56a46372, WMI-persistence). Each persistence MECHANISM counts once toward RedFlagCount (a run-key + service app gets PERSISTENCE + SERVICE_INSTALLED = 2 reds — two mechanisms, two reasons to look).
- Scope discipline (this user): these tools are discovery OUTPUT only — deny-lists, owner notifications, and triage files were explicitly declined. Don't add action outputs unless asked.

## Verifying a query's claims before the first portal run (remote/MCP)
- Enumerate the load-bearing claims (schema columns, operator semantics, retention, join keys) and verify each against primary sources. This audit class caught three real bugs in one pipeline: term-based `has` (silent dead filters), phantom `contains_any` (query error), HKCU overclaim (comment lie).
- Schema columns: ONE `firecrawl_extract` call over the MS Learn schema pages (`defender-xdr/advanced-hunting-<table>-table`) with a YES/NO exact-column-existence prompt — 6 tables, 18 columns in one call.
- Operator existence: `firecrawl_map` with `search=` on the kusto/query docs index — proves a page exists or NOT (guessing URLs 404s; the map showed `has-any-operator` exists and no contains_any page). Full operator table: `datatypes-string-operators`; cheat sheet: `kql-quick-reference`.
- Behavior claims (HKCU capture, retention) → MS Learn official answers over community blogs. Full playbook + findings table: kusto-verification.md.
- EDITING TWO-BRANCH KQL (hit 3× in one session): the radar and census branches contain near-identical blocks, and V4A patch hunks against a block existing in BOTH branches fail validation with "Found 2 matches" (fuzzy matching ignores indentation). Anchor the hunk on the UNIQUE line following the block (a branch-specific comment like `// ── AI TOOL DETECTION` or `| extend Confidence = "ExecutionOnly"`), or fall back to mode=replace whose old_string includes a line unique to that branch (`| where FileName endswith ".dll"`). Watch for the same duplication when a patch REPLACES a line that exists once per branch — a replace_all that should hit both spots silently updates only the intended sites if anchors drift.
- EXTERNAL BENCHMARK (the fresh-perspective pass — run before trusting a homegrown detection): compare against what Microsoft ships and the community: Azure/Azure-Sentinel Hunting Queries/Microsoft 365 Defender (the old microsoft/Microsoft-365-Defender-Hunting-Queries repo is DEPRECATED — pointer moved in 2025), the ASR rules reference page (attack-surface-reduction-rules-reference — lists the ADVANCED HUNTING ACTION TYPE per rule, the source of Asr*Audited/Blocked names), and community repos (Bert-JanP/Hunting-Queries-Detection-Rules, FalconFriday). Use the DIRECT Firecrawl tools only — `firecrawl_search` + `firecrawl_research_search_github` + targeted `firecrawl_scrape` of raw.githubusercontent MS docs. USER RULE (2026-07-31): do NOT dispatch `firecrawl_agent` or any delegated research — "you are an agent, you don't need something else to do what you can do". Benchmark queries surfaced real gaps here: C:\Users\Public missing, sideload subdirectory evasion, the ASR-audit-events native signal, per-user tool folders (scoop/PortableApps/OneDrive) missing from the path filter, RMM tools unclassified, the persistence blind spots (services/WMI/startup LNKs), raw-IP callbacks missing, the elevation column collected-but-unused, and the initiator map missing cloud-sync/download-manager/torrent arrivals (onedrive.exe misclassified as ChatApp). Rejected with reasons on the same pass: TLD-based origin flags (no precedent, noise).
- EXHAUSTION-AUDIT METHOD (rounds 7–13, user-driven "don't stop until multiple different searches find nothing"): when asked to keep auditing, run BATCHES of 3 independent searches (different dimensions per batch: schema mirrors, community repos, official analytics, adjacent platforms), implement what verifies, and stop only after 2+ CONSECUTIVE batches return nothing implementable. Two high-yield techniques from the exhaustion runs: (1) systematically sweep the FULL ActionType inventory for types you don't use yet — grep the saved 223-type list for unused-but-relevant names (this is how SensitiveFileRead, DpapiAccessed, ScheduledTaskCreated, ShellLinkCreateFileEvent, WmiBindEventFilterToConsumer were found); (2) diff against the official Azure-Sentinel Solutions analytics (AppInit_DLLs analytic, FileCreatedInStartupFolder, WindowsBinariesLolbinsRenamed) and adjacent-platform queries (SentinelOne Power Queries, Elastic new_terms, Splunk RMM analytic, techjack ClickOnce hunting set). Every find must be externally validated before implementing (the v3.13 registry leg was validated by three independent sources); every rejection recorded with its reason (Defender GPO-path exclusion keys NOT collected in AH; RemovableStorageFileEvent device-control-policy-gated; TLD flags no-precedent; USB-mount correlation weak). Cumulative scoreboard after 13 rounds: ~22 gaps closed, 2 wrong claims corrected (HKCU, onedrive-in-ChatApp), 3 rejected with reasons, 1 verification-only round. At exhaustion the remaining gaps are structural only: 30-day retention, COM hijacks, script-based tools (reference material in the query header), WSL (separate Linux telemetry ecosystem), the portal run itself.

## Portal run & paste-error triage (KS204 / union resolve failures)
- Error taxonomy for unresolvable names in the AH portal:
  - `union operator failed to resolve table expression named 'X'` — the union references a name that does not exist in THE TEXT THAT RAN. A single misspelled name (e.g. `ProvnencaceConfirmed` for `ProvenanceConfirmed`) = a typing/autocorrect slip in the portal copy or a stale saved query. Before blaming the file, grep the on-disk copy case-insensitively (`grep -in "provn" file`) — a misspelling found NOWHERE on disk means the executed text diverged from the file.
  - KS204 (`The name 'X' doesn't refer to any known column, table, or data function`) on MULTIPLE let-referenced names AT ONCE (e.g. all of ProvenanceConfirmed + ExecutionOnly + UserContext at the union tail) = the executed text is a FRAGMENT: none of the let definitions (hundreds of lines earlier) are in what ran. Not a typo, not a file bug. Verify each referenced name has a `^let <name>` declaration in the file, then conclude the paste/copy/saved query lost everything above the tail.
- File-integrity checks BEFORE blaming the file (all cheap, run in one batch): no BOM (`head -c 64 f | xxd` — must start with `//`); null bytes via python `data.count(b'\x00')` — NOT `grep -c $'\x00'` (bash `$'\x00'` NUL truncates grep's pattern to empty → matches EVERY line → false "everything is null"); no stray `;` lines that aren't `);`/`];` (a standalone tabular statement before the union can break let visibility / change which statement the portal runs).
- Portal paste workflow: Ctrl+A in the editor BEFORE pasting (pasting over a leftover fragment → duplicate-let errors next). After pasting, verify the FIRST line (header comment) and LAST line (final `| order by ...`) are intact and no inline KS204 squiggles remain under any let name. If long pastes truncate, split the file at a clean statement boundary — the end of a materialized let (a `));` line) — into 2 chunks, paste sequentially, ignore intermediate syntax errors until both chunks are in; verify chunk byte counts sum to the original file's.
- Renaming .kql → .txt is cosmetic — the portal takes pasted text, never file paths.

## Producer/consumer contract testing (the pair-audit pattern)
- KQL queries and their PS1 consumers drift: the KQL aliases columns (`ExampleOriginUrl`, `ExampleInitiator`) while the PS1 checks raw names (`FileOriginUrl`, `InitiatingProcessFileName_Create`) -> provenance signals silently never load, scores understate. Static review MISSED this; a runtime test caught it.
- Rule: audit the pair together; PS1 column checks should accept both names (`-or` on the column set).
- Always runtime-test the PS1 with a synthetic CSV matching the PRODUCER's actual output columns (not the consumer's assumed names), covering every scoring branch (prevalence tier, cert tier, unsigned, renamed LOLBin, persistence, sideload, macro/chat drops, NEW_APP). Gotcha: the PS1 may RENAME columns on output (`ExampleInitiatorClass` comes in, `InitiatorClass` goes out) — a verification script reading the input name from the output CSV KeyErrors while the pipeline is actually fine. Verify against the output object's real column names. See portable-app-discovery.md and scripts/gen_portable_test_csv.py.

## PowerShell verification workflow
- USER PREFERENCE (round 14): package verification as ONE .ps1 harness file run once (fixture generator + harness + assertions), not repeated inline `powershell.exe -Command` invocations — several inline invocations were denied at the approval prompt; the single harness file was approved and ran clean. Write the harness to Downloads, show its output, then delete all artifacts.
- Harness-authoring gotchas: invoking the PS1 in-process with `&` never sets `$LASTEXITCODE` (only native executables set it) — wrap in try/catch and assert no exception; re-derive expected fixture values from the CURRENT code before asserting (an unsigned malware-hit row is UNSIGNED+MALWARE_HIT=rf=2, not rf=1 — stale expectation tables cause false FAILs).
- Parse check (no execution): `$errs = $null; [void][System.Management.Automation.Language.Parser]::ParseFile('script.ps1', [ref]$null, [ref]$errs); $errs.Count`
- Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\...\script.ps1' -InputCsv '...' -OutputCsv '...'`
- PS 5.1 `Export-Csv` defaults to ASCII (mojibake on non-ASCII filenames) — pass `-Encoding UTF8`. Re-reading that CSV in python needs `encoding='utf-8-sig'` (BOM).
- `$results += [PSCustomObject]` is O(n²) — use `[System.Collections.Generic.List[object]]::new()` + `.Add()`.
- Null-guard every method call on CSV fields: `([string]$row.FolderPath).ToLowerInvariant()` — a missing column crashes the run under `$ErrorActionPreference = "Stop"` (this was the one unguarded `.ToLower()` in a scorer that otherwise guarded everything).
- `$data = @(Import-Csv ...)` — a single-row CSV yields a scalar; `.Count` renders blank in banners and `[0]` indexing gets unreliable.
- `& $script.txt` SILENTLY NO-OPS in PS 5.1: the call operator will not execute a script file whose extension isn't .ps1 — no output, no error, no $LASTEXITCODE; the pipeline just skips it (the scorer appeared to "produce no output file" with zero diagnostics). The production scorer was renamed portable.txt (same pattern as the KQL) and became un-runnable. Guard: validate `$Scorer -match '\.ps1$'` before invoking (run-ah.ps1 throws) and keep scorers as .ps1 even when the KQL lives as .txt.
- `powershell.exe -File x.txt` ALSO REFUSES non-.ps1 scripts ("does not have a '.ps1' extension", verified 2026-08) — the one-shot runner is the ONE file that must keep .ps1 even though the user renames every artifact (KQL, scorer, even the runner itself) to .txt. A renamed copy is also a STALE copy: after a source fix, the old .txt still carries the buggy embedded KQL — tell the user to delete renamed builds or they'll re-run the bug. (Context7-verified 2026-08: Graph v1.0 runHuntingQuery, lowercase schema/results, ThreatHunting.Read.All both permission types, 100k/50MB/3-min/429 quotas all match run-ah.ps1.)
- ONE-SHOT API RUNNER (2026-08): `C:\Users\<user>\Downloads\run-ah.ps1` runs the whole pipeline without the portal — ONE self-contained file: KQL + scorer are EMBEDDED (built from provenance-full.txt + portable.txt). Auth: -MgGraph (Connect-MgGraph interactive) or client credentials; POST to Graph v1.0 `POST /security/runHuntingQuery`; normalizes lowercase `schema`/`results` to CSV; scores; writes ah-raw.csv + portable-apps-final.csv + -redflagged.csv. REGENERATE after editing sources: run the one-shot API runner builder (live environment; writes UTF-8-BOM so PS 5.1 decodes embedded Unicode banners; embedded scorer runs via a temp .ps1 because PS 5.1 scriptblocks don't splat and & won't execute non-.ps1 files — verified). `-MockResponse <json>` skips auth+API (test hook + re-scoring saved responses); -QueryFile/-Scorer override the embedded copies. API execution cap ~3 min vs portal 10 min — the heavy query may time out via API (504); 429 = CPU quota, ~15-min cycle. Verified: 5-row mock (90+ asserts incl. T+B+C==rf), empty-response graceful, and self-containment proven by renaming ALL sources away and re-running.
- Single-quoted PS regex strings: `'\tools\'` is a TAB escape (`\t`), NOT a literal backslash. For literal `\tools\` write `'\\tools\\'` (2 backslashes).
- PS 5.1 reads UTF-8-*-no-BOM* .ps1 sources as ANSI: non-ASCII literals in RUNTIME strings (e.g. a "·" separator) become mojibake in console output AND get double-encoded into Export-Csv output ("·" → "Â·" when re-read as utf-8-sig). Use ASCII separators ("|") in any string the script emits. Comments are unaffected.
- When verification is a piped run (`... | head -30`), the pipe closing early kills PowerShell mid-run via broken pipe BEFORE Export-Csv executes — a "missing output file" can be a test artifact, not a bug. Use `tail` or redirect to a file so the run completes.

## WSL interop pitfalls
- WSL python does NOT understand `C:\...` paths: `open(r"C:\Users\...")` creates a FILE whose literal name contains backslashes (or fails). Always use `/mnt/c/...` in WSL-side code; only PowerShell/Windows tools get `C:\...` paths.
- `powershell.exe` invoked from WSL needs full Windows paths for -File/-InputCsv arguments.

## References
- portable-app-discovery.md — provenance-full.kql <-> portable-app-discovery.ps1 column contract, v3.3 NO-SCORE design (RedFlagCount + buckets + flags), v3.1 readability layer (Families partition/LoudSignal/Profile), behavioral installer detection (uninstall-key/msiexec-child/file-volume), test expectations, v2 → v3.14 evolution (TVM vendor join, radar+census merge, has→contains, contains_any correction, scoring drop, Public paths, sideload subdir, ASR + TVM-evidence knobs, \\Users\\ catch-all, RMM, psexec/WMI, persistence expansion services/WMI/startup-LNK + HKCU correction, raw-IP callbacks, ELEVATED, initiator-map CloudSync/DM/Torrent classes + onedrive bug, materialize on double-referenced lets, ProgramData + choco, AV/PUA verdicts, actor-behavior events, *Portable.exe name discovery, registry-persistence leg, self-deletion, DPAPI, exhaustion-audit rounds, audit scoreboard)
- deviceevents-actiontypes.md — verified DeviceEvents ActionType knowledge bank: how to pull the full inventory (xdrinternals + double-parse gotcha), the exact names + audit-gating of every persistence/ASR/WDAC-relevant ActionType, and what the v3.6 persistence expansion changed
- kusto-verification.md — claim-verification playbook (firecrawl_extract schema checks, firecrawl_map operator-existence check, findings table, fix patterns that survive verification)
- scripts/gen_portable_test_csv.py — synthetic 7-row fixture generator for the discovery pipeline


## Reference: portable-app-discovery.md

# Portable app discovery pipeline — column contract & scoring design

Pair: `provenance-full.kql` (MDE AH) -> CSV export -> `portable-app-discovery.ps1` from the enterprise-application-control skill (flag tally & RedFlagCount — NO scores since v3.3).
User context: ~[fleet size], MDE AH portal (NOT Sentinel — TVM/Alerts tables unavailable there).

## Column contract (KQL output -> PS1 input)

PS1 auto-detects columns and degrades gracefully, but these names MUST match for signals to load:

| KQL output column (full) | PS1 expects | Status |
|---|---|---|
| ExampleOriginUrl | FileOriginUrl OR ExampleOriginUrl | PS1 v2 accepts both (drift fixed) |
| ExampleInitiator | InitiatingProcessFileName_Create OR ExampleInitiator | PS1 v2 accepts both |
| TopFolderPath | FolderPath (PS1 output) | **PS1 accepts both (drift fixed)** — KQL renamed FolderPath→TopFolderPath in both branches' summarize (take_any); PS1 read $row.FolderPath → output path was EMPTY for every row. Same alias pattern as ExampleOriginUrl. |
| DistinctDays (was MaxDistinctDays) | DistinctDays | renamed in KQL v2 |
| ExecutionCount (was TotalExecutions) | ExecutionCount | renamed in KQL v2 |
| ExampleInitiatorClass | ExampleInitiatorClass | match |
| IsSigned / IsTrusted | IsSigned / IsTrusted (bool -> True/False in CSV) | match |
| GlobalPrevalence / ProfileAvailability / IsCertificateValid / ThreatName | same (from FileProfile) | match |
| UsersSample (make_set of UPNs, fleet-wide) | UsersSample | added v2 |
| PathCategory / ScriptLaunches / SystemLaunches / ExplorerLaunches / InstallerLaunches | same names | added v3.2 (launcher counts are countif on InitiatingProcessFileName — the launcher, not the grandparent) |
| IsInstaller / IsInternalTool | same names | added v3.2 (IsInternalTool needs Signer in the census branch's cert projection — easy to forget) |
| LauncherBreakdown | PS1-built display string from the 4 counts | added v3.3 |

PS1 gotcha if columns drift: `DistinctDays` backfilled with 1 -> usage component flat at 0.5 for every row; silent.

## Scoring design — v3.3: NO SCORES (user-driven; do not reintroduce)

Both 0-10 composites (Portability, Risk) were DROPPED on 2026-07-31 after the analyst reported risk was "nigh impossible to categorize" (mouseclicker.exe: signed + globally prevalent + clean -> Risk 0, yet exactly the ungoverned app you want to see) and asked "are we overfitting? should we just drop risk entirely?" — the answer was yes. Weighted composites overfit without labeled data: every tuning round was one weight per complaint (sideload +3→+1 after 7-Zip, TVM join rebuilt after it never matched). A composite also lies by omission: Risk 0 reads "reviewed, fine" when it means "nobody judged this". The Decision carry-over + Growth KPI + flags were doing the actual work all along.

Replacement = facts + booleans + ONE unweighted tally:
- RedFlagCount: 1 point per independent red-flag boolean: UNSIGNED*, LOW_PREVALENCE* (gp<100), SCRIPT_LAUNCHED, PERSISTENCE, RENAMED_LOLBIN, DOWNLOAD_CRADLE, ENCODED_CMD, NONSTD_PORT, ALERT_HIT (incl. ThreatName), TEMP_EXECUTION, SIDELOAD_DLL, SPOOFED_METADATA, USER_OVERRIDE. (*suppressed when IsInternalTool — expected state.) No weights: "how many reasons to look" is a tally, not a judgment. Sort desc.
- Flags that DON'T count (facts/notes): TRUST_MIXED, SYSTEM_LAUNCHED, NETWORK_SHARE, USB_EXECUTION, OFFICE_DROP, CHAT_DROP, INSTALLER, INSTALLER_ORIGIN, INTERNAL_TOOL, INTERNAL_UNSIGNED (the "should be signed" finding), AI_TOOL, NEW_APP, RENAMED:<orig>, NO_METADATA.
- SIGNED_PREVALENT: signed + gp>=10000 + zero red flags = "looks fine, isn't governed" — makes signed shadow IT surface instead of zeroing out.
- Buckets (precedence): RedFlagged (rf>=2 AND not internal) > Internal > New (not in PreviousCsv) > Installer > Stable.
- Output files: main CSV + <base>-redflagged.csv (Bucket = Loud or RedFlagged). IsTrusted "Mixed" still = TRUST_MIXED flag only. Decision carry-over + Growth KPI unchanged.

## KQL v2 structural notes (fixed bugs worth remembering)

- Run-key persistence: `tostring(parse_path(RegistryValueData).Filename)` — was `.FileName` (dead). Filter `RegistryKey contains @"\CurrentVersion\Run"` (v3.1: was `has`, term-broken). Hive coverage: REVISED v3.6 — the earlier "HKLM only (per MS answers/questions/3978033)" claim is contradicted by community runbooks querying HKCU paths in DeviceRegistryEvents directly (Crimson7research, forenza.io COM-hijack hunts); the contains filter matches either hive, so treat both as covered.
- DLL sideload step: `summarize SideloadedUnsignedDlls = make_set(FileName, 5) by SHA1 = InitiatingProcessSHA1` — was `by InitiatingProcessSHA1 = SHA1` (DLL's own hash, mislabeled -> join key missing on right side -> whole query errored).
- FileProfile insert: `project-away Signer, Issuer, IsRootSignerMicrosoft, SoftwareName, SoftwareVendor` BEFORE `| invoke FileProfile(SHA1, 1000)`.
- Two persistence task columns (schtasks -> PersistenceTask, Register-ScheduledTask -> PersistenceTaskPS) then merged; same column name from two joins gets auto-suffixed "1" — use distinct names.
- Creation lookback 90d vs execution 30d: inner join on (DeviceName, SHA1) requires both events in-window; 30d/30d misses files created before the window (first-run blind spot).
- ChatApp class added: teams/ms-teams/slack/telegram/whatsapp/zoom/discord/signal/onedrive.
- Configurable lets at top: ExtraPortableRoots, StandardPorts (22/445/3389/8443/8888/8000/3000 added).

## Runtime test recipe (what the v3.3 verification run proved)

7-row synthetic CSV (47 columns, v3.2 KQL output shape) with expected results:
- internal tool (IsInternalTool=True, unsigned, gp 80, 2 system launches, 118 explorer) -> rf=0, flags UNSIGNED INTERNAL_UNSIGNED LOW_PREVALENCE SYSTEM_LAUNCHED INTERNAL_TOOL, bucket Internal (suppression works)
- mouseclicker (signed, gp 500000, clean, browser origin) -> rf=0, SIGNED_PREVALENT, bucket Stable, Decision=Allow carried from PreviousCsv
- payload (unsigned, gp 50, 3 script launches, Temp path, renamed cmd.exe, encoded cmd, persistence, sideload, nonstd port) -> rf=10, Loud
- FirefoxSetup.exe (signed installer, in prev run, OriginalFileName=setup.exe) -> rf=0, flags INSTALLER SIGNED_PREVALENT RENAMED:setup.exe, bucket Installer
- renamed LOLBin (OriginalFileName=cmd.exe, unsigned) -> rf=2 (UNSIGNED + RENAMED_LOLBIN), Loud
- share execution (UNC FolderPath, unsigned, gp 3000, 1 script launch) -> rf=2, NETWORK_SHARE flag, RedFlagged
- macro drop (OfficeMacro class, unsigned, gp 30, Temp) -> rf=3 (UNSIGNED + LOW_PREVALENCE + TEMP_EXECUTION), OFFICE_DROP/NEW_APP + NO_METADATA flags, RedFlagged
Bucket totals: 2 Loud / 2 RedFlagged / 1 Internal / 1 Installer / 1 Stable. Growth Stable/New as designed; Quarantine decision carried.
Edge: old-shape CSV (no PathCategory/launcher/IsInstaller/IsInternalTool columns) + single-row CSV both run clean — all new columns guarded (rf still counts UNSIGNED etc.).

Generator: scripts/gen_portable_test_csv.py (writes portable-test-input.csv + portable-test-prev.csv under /mnt/c/Users/<user>/Downloads; run from WSL, then invoke the PS1 (enterprise-application-control skill) with -InputCsv/-PreviousCsv).

## Test data pitfalls (learned the hard way)

- Generator rows must be EXACTLY 47 columns; a missing TopFolderPath field shifts every column after it (scores look crazy, values land in wrong columns). Assert field count per row before writing.
- WSL python: write the CSV to /mnt/c/... path; a Windows-style path becomes a file literally named `C:\Users\...` — remove with `rm -f 'C:\Users\<user>\Downloads\portable-test-input.csv'` (quoted).
- PS 5.1 Export-Csv writes UTF-8 BOM — python re-read needs encoding='utf-8-sig' or header lookup KeyErrors.

## v2.1 → v3.1 evolution

- TVM check rebuilt: name equality (`ShortName == SoftwareName`) never matched — TVM names carry versions. Now a vendor-presence join: `on $left.CompanyName == $right.VendorMatch` against distinct TVM `SoftwareVendor`. Deleted the ShortName substring machinery (~6 lines of dead weight).
- Sideload: +3 → +1 (see risk section). 7-Zip's 7z.dll example: an unsigned DLL next to an unsigned exe is the portable packaging pattern, not T1574.002.
- v3 (consolidation, user-driven "why not just 1 kql?"): portable-sweep.kql MERGED into provenance-full.kql — one file, two branches:
  - `ProvenanceConfirmed` = radar (creation+execution inner join, full enrichment)
  - `ExecutionOnly` = census (leftanti on branch 1, `DistinctDays >= 2`, lean enrichment: TVM vendor + cert True/False/Mixed + FileProfile + `IsUnknown` = unsigned & GlobalPrevalence < 100)
  - `union` (default kind=outer pads missing columns with nulls — safe; no same-name-different-type collisions here) + `Confidence` column
  - FileProfile invoked PER BRANCH — each keeps its own 1000-file cap (the big branch can't starve the small one)
  - `UserContext` (mv-expand UPN drill-down) computed once unscoped — branch scoping would be circular — joined after the union
  - PS1 v2.2: Confidence + IsUnknown carried through the output
- v3.1 (verification-driven): `has` term-semantics bug fixed — punctuated `has` patterns NEVER match (terms are alphanumeric sequences):
  - path filters → `contains`, `has "/create"` → `contains`, run-key filter → `contains`
  - ExtraPortableRoots → `matches regex` alternation `@"(?i)C:\\Tools\\|C:\\Portable\\|C:\\Utils\\"` (let stays the single knob)
  - AI-tool lists → or-chains of `contains` (25 name + 12 company + 7 product conditions, all case-insensitive)
  - both task joins → `tostring(parse_path(TaskAction).Filename)` + `==` equality (whole-filename match, also more precise)
  - bool comparisons → `IsSigned != true or isnull(IsSigned)` (bool literals, not string "True")
  - HKCU claim corrected (HKLM only). Impact: AppData/Temp discovery and ALL persistence detection were dead before this — expect more candidates and PersistenceDetected firing after the query lands in the portal.
- v3.2 (MCP-verification follow-up): `contains_any` does NOT EXIST in Kusto (verified: full operator table + quick reference + docs map show only has_any/has_all in the `_any` family) — the v3.1 patch had used it in 5 places (would have errored in the portal). Replaced with the `matches regex` alternation and the contains or-chains above.
- v3.3 (scoring drop — user-driven, see "Scoring design" section above): KQL gained PathCategory (case order: Temp before AppDataLocal*, AppDataLocalPrograms before AppDataLocal, Downloads/Desktop before UserHome), launcher countifs, IsInstaller, IsInternalTool (InternalPublishers regex let — placeholder contoso|fabrikam, fill per org), UNC share discovery (`FolderPath startswith @"\\"` in ExecutedFiles AND the sideload DLL filter), installer name-exclusion REMOVED from ExecutedFiles, Signer added to the branch-2 cert projection. PS1 v3 dropped both scores; new flags: SCRIPT_LAUNCHED, SYSTEM_LAUNCHED, TEMP_EXECUTION, NETWORK_SHARE, USB_EXECUTION, INSTALLER, INTERNAL_TOOL, INTERNAL_UNSIGNED, SIGNED_PREVALENT, USER_OVERRIDE, ALERT_HIT, INSTALLER_ORIGIN.
- Persistence coverage limits documented in the query: Run keys + schtasks/Register-ScheduledTask only; Startup-folder LNKs, services, WMI, COM hijacks NOT visible in AH. "PersistenceDetected=False" ≠ "no persistence".
- Scope: this toolchain is discovery OUTPUT only — deny-lists, owner notifications, approved-signer triage were explicitly declined. Don't add action outputs unless asked.

## v3.4 (fresh-perspective audit, MCP-verified — all implemented)

- C:\Users\Public added to the discovery filter (ExecutedFiles AND the sideload DLL filter) and to PathCategory ("Public", before the UserHome fallback). PS1: PUBLIC_STAGING flag (flag-only — shared tools are legit, it's context).
- Sideload check relaxed to same-folder-OR-SUBDIRECTORY: `tolower(tostring(parse_path(FolderPath).DirectoryPath)) startswith tolower(tostring(parse_path(TopFolderPath).DirectoryPath))` — startswith is safe because DirectoryPath carries a trailing backslash, so "App2\" can't false-match "App\" (Elastic's documented subdirectory-evasion fix; flag-only so extra FPs are cheap).
- New lets: `AsrAuditEvents` (DeviceEvents ActionType in AsrUntrustedExecutableAudited/Blocked + AsrUntrustedUsbProcessAudited/Blocked -> AsrUntrustedHits by SHA1) and `TvmFileEvidence` (DeviceTvmSoftwareEvidenceBeta, mv-expand DiskPaths -> lowercase distinct EvidencePath).
- OPTIONAL-JOIN KNOB PATTERN: `let UseAsrSignals = true; let UseTvmFileEvidence = true;` then `| join kind=leftouter (XLet | where UseX) on Key` — when the knob is false the source filters to an empty table and the leftouter pads nulls (inert, no error; Kusto has no tabular if/else). Flip to false if the ASR rules aren't deployed or the beta table breaks.
- Both branches joined: `AsrUntrustedHits` (-> ASR_UNTRUSTED red flag, +1 RedFlagCount — Microsoft's own cloud verdict counts like any signal) and `InTvmFileEvidence` True/False (fact column; take_any caveat: candidates carry ONE sampled path so multi-user apps under-report — vendor match stays primary).
- v3.4 regression verified (2026-07-31): Public + 2 ASR hits -> rf=2 RedFlagged (PUBLIC_STAGING + ASR_UNTRUSTED); Temp + ASR + gp80 -> rf=5; signed + prevalent + InTvmFileEvidence=True -> rf=0 SIGNED_PREVALENT Stable; old-shape CSV (no new columns) runs clean.
- Portal checks still owed: confirm rules 01443614/b2b3f03d actually deployed (`DeviceEvents | where ActionType startswith "AsrUntrusted" | summarize by ActionType` — empty result = flip UseAsrSignals to false); DeviceTvmSoftwareEvidenceBeta name/columns may change on GA (one-line rename behind the knob).

## v3.1 PS1 readability layer (no scores, but readable — user: "in a way that doesn't lie but makes it easier to read/categorize")

The honesty rule that makes this safe: a score doesn't lie when it's an invertible function of displayed facts — every point maps 1:1 to a visible flag, no hidden weights, no caps/floors. Three additions, all derived from existing inputs:

- **Families**: "T2 B6 C1" — the red flags are grouped Trust (UNSIGNED, LOW_PREVALENCE, ASR_UNTRUSTED, USER_OVERRIDE, SPOOFED_METADATA) / Behavior (SCRIPT_LAUNCHED, ALERT_HIT, MALWARE_HIT, RENAMED_LOLBIN, DOWNLOAD_CRADLE, ENCODED_CMD, PERSISTENCE, SIDELOAD_DLL, NONSTD_PORT) / Context (TEMP_EXECUTION, RMM_TOOL). It's a PARTITION of RedFlagCount: T+B+C==rf by construction. **Test invariant**: parse the Families column and assert the sum equals RedFlagCount on every row — a patch dropped one `$c++` (Temp case) and only the invariant caught it.
- **LoudSignal**: True when any of the documented threat-shaped list fires — MALWARE_HIT, ALERT_HIT, PERSISTENCE, RENAMED_LOLBIN, ENCODED_CMD, DOWNLOAD_CRADLE, ASR_UNTRUSTED. Category, not weight. Bucket precedence became **Loud > RedFlagged > Internal > New > Installer > Stable**; sort key LoudSignal desc first. Verified distinction: renamed cmd.exe (rf=2, loud) outranks a macro-drop temp payload (rf=3, not loud).
- **Profile**: "Signed | Prevalent | Established" — trust state (Signed/Untrusted/Unsigned), prevalence band (Rare <1000 / Common <100000 / Prevalent), age band (New <30d / Established); "?" when the input is unavailable (e.g. no FileProfile row -> "Unsigned | ? | Established"). Thresholds are visible constants in the code, not hidden weights. Same triad as ASR rule 01443614.
- PS 5.1 gotcha discovered by the terminal: "·" separators became mojibake (UTF-8-no-BOM source read as ANSI, double-encoded into the CSV) — ASCII "|" separators.

## v3.5 (second fresh-perspective audit — path universe + RMM + remote-launch, all implemented)

- **Path filter simplified to the \Users\ catch-all**: `FolderPath contains @"\Users\"` + Windows\Temp + ^[D-Z]:\ + ExtraPortableRoots + UNC. The old specific patterns (Downloads/Desktop/AppData/Public) were subsumed; the catch-all ADMITS what they missed: scoop (`C:\Users\<u>\scoop\apps\...`), PortableApps (`C:\Users\<u>\PortableApps\...`), OneDrive-synced tools, custom user tool dirs. PathCategory gained `Scoop` and `PortableAppsFolder` (checked before the UserHome fallback); PS1 flags SCOOP_MANAGED, PORTABLEAPPS (flag-only). Sideload DLL filter simplified the same way.
- **IsRmmTool (T1219)**: name/company contains-chains in both branches, same shape as the AI list. List: anydesk, teamviewer, rustdesk, screenconnect, connectwise, splashtop, ammyy, dwservice, parsec, gotomypc, logmein, ultravnc, tightvnc, realvnc, remoteutilities, aeroadmin, meshcentral, tacticalrmm, supremo, zohoassist, chromeremote + company matches. PS1: RMM_TOOL is a RED flag (+1, Context family) — decision made because the v3.5 test showed a signed+prevalent AnyDesk otherwise lands rf=0 and sinks; a portable RMM tool is review-worthy by definition.
- **PsexecWmiEvents let**: `AsrPsexecWmiChildProcessAudited/Blocked` (rule d1e49aac) -> RemoteLaunchHits, joined in both branches behind UseAsrSignals. PS1: REMOTE_LAUNCHED flag (flag-only — legit remote admin exists).
- v3.5 regression verified (2026-07-31): scoop hurl.exe -> SCOOP_MANAGED rf=1 Stable; PortableApps KeePassXC -> PORTABLEAPPS rf=0 Signed|Common|Established; AnyDesk -> RMM_TOOL rf=1 (T0 B0 C1) bucket Installer; psexec-launched portscanner -> REMOTE_LAUNCHED rf=1; OneDrive synctool -> UserHome category rf=1. Invariant T+B+C==rf OK on all 5 rows. Test artifacts cleaned.
- Still owed in the portal: confirm ASR rules 01443614/b2b3f03d/d1e49aac deployment; first real run will show whether the \Users\ catch-all floods the census (expected: many signed+prevalent per-user installs land rf=0/SIGNED_PREVALENT — bounded noise by design, review list unaffected).

## v3.6 (third audit — persistence widened; HKCU claim corrected)

- Persistence coverage expanded from "Run keys + schtasks only": SERVICES (`ServiceInstalled` — event 4697, requires the "Audit Security System Extension" audit setting; inert without it), WMI event subscriptions (`WmiBindEventFilterToConsumer` — audit-independent), startup-folder LNKs (DeviceFileEvents FileCreated + `FolderPath contains @"\Startup\"` + InitiatingProcessSHA1 = candidate). COM hijacks remain the only unqueryable class.
- ASR join extended with `AsrAbusedSystemToolAudited/Blocked` (rule 56a46372 — MS's own copied/impersonated-system-tool verdict, the thing RENAMED_LOLBIN approximates) and `AsrPersistenceThroughWmiAudited/Blocked`; flag renamed ASR_UNTRUSTED → ASR_VERDICT (4 rule families now).
- PsexecWmiEvents extended with `ProcessCreatedUsingWmiQuery` (audit-independent WMI process creation — the remote-launch signal that works WITHOUT the ASR rule deployed).
- Source: full 223-type DeviceEvents ActionType inventory from xdrinternals.com — MS Learn documents columns only; the values live in the in-portal schema reference. Verbatim confirmation: all three Asr* families we use are spelled exactly right. No `WmiBindingEvent` exists (it's WmiBindEventFilterToConsumer).
- PS1 flag semantics: SERVICE_INSTALLED red/Behavior/NOT loud (signed portable DB server stays Stable — verified); WMI_PERSISTENCE red/loud; STARTUP_LNK red/loud. Each persistence MECHANISM counts once toward RedFlagCount.

## v3.7 (fourth audit — network + elevation)

- RAW_IP_CALLBACKS: `RawIpConnections = countif(isempty(RemoteUrl) and isnotempty(RemoteIP) and RemoteIPIsPrivate == 0)` added to the network summarize. Red flag, Behavior, not loud. RemoteIPIsPrivate column verified; numeric `== 0` compare is safe whether int or bool.
- ELEVATED: ProcessIntegrityLevel "High"/"System" → red+1, Behavior, not loud. Lesson: audit fact columns for signals collected-but-never-consumed. Verified: unsigned+elevated → rf=2 RedFlagged; signed+elevated → rf=1 Stable.
- DeviceFileEvents ActionTypes verified: exactly FileCreated / FileDeleted / FileModified / FileRenamed.
- TLD-based origin analysis considered and REJECTED: no community precedent in MDE, high noise potential.

## v3.8 (fifth audit — initiator map + performance)

- Initiator-class map extended: new CloudSync (onedrive/dropbox/googledrivesync/googledrivefs/megasync/pcloud/boxsync/syncthing/rclone), DownloadManager (idman/fdm/aria2c/jdownloader/xdman/eagleget/nettransport/orbitdm/freedownloadmanager), Torrent (qbittorrent/utorrent/bittorrent/transmission/deluge/vuze/tixati) classes; BUG FIXED: `onedrive.exe` was misclassified as ChatApp; WPS/LibreOffice (soffice.bin) → OfficeMacro; added vivaldi/palemoon/waterfox, mailbird/emclient/foxmail, wechat/line/viber/element, winzip64/bandizip. Files arriving via a missing class fell to "Other" → the arrivals radar missed them entirely. Approach validated by Microsoft's own suggested "Downloads" query (InitiatingProcessFileName =~ "firefox.exe" style).
- materialize() on lets referenced by BOTH branches: AsrAuditEvents, PsexecWmiEvents, TvmFileEvidence, CertInfo, TvmVendors — each was computed TWICE per run. Syntax `let X = materialize(( ... ));`. ExecutedFiles/UserContext deliberately NOT materialized — 5GB materialize-cache cap can ABORT the query on a large fleet (docs: benchmark before use).
- PS1: CLOUD_SYNCED / DM_DROP / TORRENT_DROP context flags (flag-only).
- Test-harness gotcha: the PS1 RENAMES the column on output (ExampleInitiatorClass in, InitiatorClass out) — the verification script read the input name from the output CSV and KeyErrored; the pipeline was fine.
- Cumulative audit scoreboard (5 rounds): ~13 gaps closed, 2 wrong claims corrected (HKCU coverage, onedrive-in-ChatApp), 2 additions rejected with reasons (TLD flags, materialize-on-big-tables). Portal checks still owed: ASR rule deployment probe, beta-table name, first real run.

## v3.9 (seventh audit — ProgramData, a real blind spot)

- `C:\ProgramData` was COMPLETELY invisible: not under \Users\, not Windows\Temp, not a drive root, not an extra root. Two independent confirmations: Chocolatey's official docs ("shims resolve to C:\ProgramData\chocolatey\bin") and repeated threat-report callouts (Cybereason: Emotet random-named DLLs staged in %ProgramData%; Black Basta's red-flag directory list; the DFIR Report's staging analysis).
- Fix: `or FolderPath contains @"\ProgramData\"` in the ExecutedFiles filter AND the sideload DLL filter. PathCategory order matters: `\chocolatey\` → "Choco" (CHOCO_MANAGED, package-managed = low-priority but visible) BEFORE the generic `\ProgramData\` → "ProgramData" (PROGRAMDATA_STAGING, flag-only context).
- Verified (2026-07-31): choco-shimmed terraform (signed+prevalent) → CHOCO_MANAGED + SIGNED_PREVALENT, rf=0, Stable; random-named renamed exe in ProgramData root (the literal Emotet staging shape) → UNSIGNED + LOW_PREVALENCE + PROGRAMDATA_STAGING + RENAMED, rf=2, RedFlagged. Invariant OK.

## v3.10 (eighth audit — Defender AV/PUA verdicts)

- Signal family never consumed: DeviceEvents `AntivirusDetection` + `AntivirusMalwareBlocked` — the ActionType descriptions explicitly cover "malware, potentially unwanted applications or suspicious behavior". This is the PUA layer: hacktools/keygens/activation tools that get local-engine flags without ever rising to alert status (distinct from AlertEvidence and FileProfile ThreatName).
- Fix: materialized `AvDetections` let (count by SHA1), joined in BOTH branches with no knob (AV is always on). PS1: AV_FLAGGED red +1, Trust family, NOT loud.
- Verified: PUA-flagged unsigned keygen → AV_FLAGGED + UNSIGNED, rf=2, RedFlagged; clean signed+prevalent tool → rf=0 Stable.
- Audit scoreboard (8 rounds): 15 gaps closed, 2 wrong claims corrected, 2 additions rejected with reasons, 1 verification-only round (round 6 — see below). Remaining known gaps unchanged: portal execution, script-based tools, 30-day retention.

## Round 6 — verification-only round (no changes; findings recorded)

- Microsoft's own FileCreatedInStartupFolder query (Azure-Sentinel, Malware Protection Essentials) validates the v3.6 startup-LNK detection shape.
- Official msiexec-abuse queries (detect-malcious-use-of-msiexec — yes, typo in the repo) — covered behaviorally by the installer detection.
- Official "new processes" query = prevalence-census (dcount(ComputerName) by FileName + rightanti) — same philosophy as IsUnknown + the census branch.
- Scheduled-task steps self-audited for the v3.1 term-broken-`has` trap class: clean (contains "/create", whole-word has "Register-ScheduledTask", proper /tr extraction).
- ASR 01443614 is GLOBAL (no published folder list) — nothing to diff the path filter against.
- Script-tools gap: canonical extension list recorded in the query header (SentinelOne Power Queries startup-drop detection): bat cmd dll hta jar js jse msi ps1 psd1 psm1 scr url vba vbe vbs wsf exe; pattern powershell.exe + `-File` + user-writable script path.
- Lesson: after enough audit rounds, a pass can legitimately return zero gaps — say so explicitly instead of inventing work; the signal that audits are converging is verification-only rounds.

## v3.11 (ninth audit — actor-behavior events: the candidate DID something)

- Join rule that matters: for these DeviceEvents the event's OWN `SHA1` is the TARGET file/process; the candidate is `InitiatingProcessSHA1`. Joining on SHA1 never matches candidates — always join actor-behavior events on the actor hash.
- One materialized `ActorBehaviorEvents` let (both branches): `SensitiveFileRead` (ssh keys/Outlook archives — credential access; SENSITIVE_READ red+loud), `OpenProcessApiCall`/`ReadProcessMemoryApiCall`/`WriteToLsassProcessMemory`/`ProcessPrimaryTokenModified` (injection primitives; TAMPERING_APIS red, NOT loud — debuggers/anti-cheat overlap), `FileTimestampModificationEvent` (timestomping; TIMESTOMP flag-only — extractors/backups legitimately restore timestamps), `ShellLinkCreateFileEvent` (SHELL_LINK_CREATION flag-only — MS Learn Q&A validates the action type; installers creating shortcuts is normal).
- AsrAuditEvents gained `AsrScriptExecutableDownloadAudited/Blocked` (JS/VBS launching downloaded exes).
- Verified: sensitive-reader → Loud rf=2; tampering tool → RedFlagged rf=2 (not loud); timestamper → Stable rf=1 TIMESTOMP only.

## v3.12 (tenth audit — name-based discovery: PortableApps.com-format launchers)

- The official PortableApps.com Format spec: launcher is `AppNamePortable.exe` at the folder root, and apps "run in local mode from anywhere" — a C:\-root `FirefoxPortable.exe` is invisible to every path filter. Fix: `or FileName endswith "Portable.exe"` in the discovery filter (name-based admission, case-insensitive) + PathCategory "PortableLauncher" (checked after PortableAppsFolder so the folder convention wins; PORTABLE_LAUNCHER flag).
- Verified: C:\FirefoxPortable\FirefoxPortable.exe (signed, prevalent) → PORTABLE_LAUNCHER + SIGNED_PREVALENT, rf=0, Stable — previously invisible.
- Same batch: Intune "Discovered apps" is registry/WMI-tracked installs only (unmanaged apps never collected on personal devices) — the query covers the portable layer Intune can't see (header note).

## v3.13 (eleventh audit — self-deletion + registry persistence leg)

- SELF-DELETION (T1070.004): candidate deleted a file with its own name. Recipe: DeviceFileEvents `FileDeleted` → inner join candidates on InitiatingProcessSHA1 → `where FileName == FileName1` (post-join: left FileName = deleted file, right FileName1 = candidate name) → SELF_DELETED red+loud. Radar-branch ONLY (scoping needs ProvenanceCandidates; branch-2 scoping circular). Validated externally: AcidPour/RansomHub/ProLock all self-delete; MITRE's documented detection strategy is "monitor for processes that delete their own executable".
- Registry-persistence leg (the run-key join is still the value-data-parsing leg; this new leg joins on InitiatingProcessSHA1 = candidate DID the write): `AppInit_DLLs` (T1546.010 — official Azure-Sentinel analytic exists), `Image File Execution Options` Debugger (T1546.012), `Winlogon` Shell/Userinit (T1547.004 — Cofense persistence reference), service `ImagePath` under `\CurrentControlSet\Services\` (T1543.003 — audit-INDEPENDENT service creation; detect.fyi validates the key path). All four feed PersistenceDetected.
- RunOnce verified as already covered: `contains @"\CurrentVersion\Run"` matches `...\CurrentVersion\RunOnce` as substring (Cyb3r-Monk T1547.001 covers the same set).
- DOCUMENTED DEAD-END: Defender-exclusion tampering — the interesting GPO-path key (`HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Exclusions`) is NOT collected in AH (cloudbrothers research); the monitored non-policy key is locked down. No tampering join possible.

## v3.18 (round 17 — context7-verified; four contract/behavior bugs)

- **`has` on hyphenated strings = dead persistence leg (the big one).** The
  Register-ScheduledTask/Set-ScheduledTask leg used `ProcessCommandLine has
  "Register-ScheduledTask"` — hyphens break Kusto terms, so the filter NEVER
  matched and the PowerShell task-creation persistence leg was silently dead
  since v3.1. The round-6 self-audit called it "clean" because it only checked
  whole-word-ness, not hyphenation. Fix: `contains`. LESSON: when auditing for
  the term-broken-`has` class, check for ANY non-alphanumeric in the RHS
  (hyphens, not just dots/slashes/backslashes).
- **Branch 2 lacked IsAITool** (branch 1 only) — ExecutionOnly census rows never
  got AI_TOOL. The same name/company/product list now runs in both branches.
  Lesson: when a flag/list is added to branch 1, check branch 2 for the same
  class of signal (IsRmmTool had been mirrored, IsAITool hadn't).
- **Branch 1 lacked the CertSigner fallback** (branch 2 had it): branch 1
  projected away Signer before FileProfile without carrying the cert signer, so
  candidates past the 1000-file cap were misclassified IsInternalTool=False.
  Now: `extend CertSigner = Signer` before project-away, IsInternalTool matches
  Signer OR CertSigner, then project-away.
- **PS1 FolderPath column read $row.FolderPath but both KQL branches emit
  TopFolderPath** — the output CSV's path column was empty for EVERY row (the
  alias class of the ExampleOriginUrl drift, but on the output side). Fix:
  `FolderPath=if($columns -contains "TopFolderPath"){$row.TopFolderPath}else{$row.FolderPath}`.
  Runtime-verified: 3-row contract test (TopFolderPath input) → FolderPath
  populated in output, AI_TOOL fires on ExecutionOnly row, T+B+C==rf holds.
- Verified via context7 (/microsoftdocs/defender-docs) this round:
  AntivirusDetection is a real ActionType (MS's own PUA query uses it),
  DeviceFileCertificateInfo has IsSigned/IsTrusted, DeviceNetworkEvents has
  RemoteIPType, FileProfile's second arg is a 1-1000 record cap (not a time
  window), has/contains both exist in Kusto.

## v3.17 (round 16 — task-modification persistence + tampering + perf; all MCP-verified)

- **Task MODIFICATION persistence was uncovered** (T1053.005 = create AND modify): added
  ScheduledTaskUpdated (native DeviceEvents type — "A scheduled task was updated";
  verified in the 182-type inventory + IBM sample events + kqlquery.com timeline shows it
  AH-available) to the task leg; schtasks CLI leg gains /change; Register-ScheduledTask leg
  gains Set-ScheduledTask. ScheduledTaskEnabled/Disabled/Deleted deliberately excluded
  (removal isn't persistence; enable carries no content evidence). The full-inventory sweep:
  extract mandikgoyal/M365D_table README (all AH action types, one document) and diff against
  query usage — the sweep also surfaced TamperingAttempt, AsrVulnerableSignedDriver*,
  RemoteWmiOperation, UserAccountCreated, CFA violations, NamedPipeEvent, SecurityLogCleared.
- **TamperingAttempt added** (T1562.001 — "An attempt to change Microsoft Defender XDR
  settings was made") → DefenderTamperHits column → PS1 DEFENDER_TAMPERING red+B+LOUD.
  Attribution verified: community/MS tampering hunts project InitiatingProcessFileName from
  these events (RedSun_Undefend repo, hackerxone tampering query) — the initiating-process
  fields are populated, so the actor-hash join is NOT a dead leg.
- **AsrVulnerableSignedDriverAudited/Blocked** added to the ASR join (BYOVD verdict, same
  UseAsrSignals knob, same AsrUntrustedHits column).
- **Rejected with reasons**: RemoteWmiOperation (actor likely wmiprvse.exe locally — the
  round-15 dead-leg class; unverifiable without portal), UserAccountCreated/SecurityLogCleared
  (attribution unverified), NamedPipeEvent/WriteProcessMemoryApiCall/NtProtectVirtualMemoryApiCall
  (universal legit behavior — no decision value), ControlledFolderAccessViolation* (CFA
  protects Documents/Desktop by default — legit portable apps writing documents would FP),
  GetAsyncKeyStateApiCall/GetClipboardData/LdapSearch/AuditPolicyModification/CredentialsBackup
  (round-14 rejections stand).
- **StartupFiles tightened**: `contains @"\Startup\"` → `contains @"\Start Menu\Programs\Start"`
  — matches both FOLDERID_Startup and FOLDERID_CommonStartup (KNOWNFOLDERID docs) via the
  shared prefix; the old filter matched any unrelated folder literally named "Startup".
- **Branch-2 leftanti now uses ProvenanceCandidates** instead of ProvenanceConfirmed —
  row-set identical (all enrichment joins are row-preserving leftouter) but avoids
  recomputing the full branch-1 pipeline + its FileProfile invoke. materialize() docs:
  non-materialized lets get recalculated per reference.
- **ProvenanceCandidates now materialized** — ~13 references vs the settled design's 2× lets;
  bounded size (summarized candidate set) makes the 5GB-cache abort risk negligible; the
  docs' benchmark caution is noted in the comment. (Extends the round-14 materialize list.)
- **.com added** to both executable-extension filters (UserIntroducedFiles + ExecutedFiles) —
  elastic/detection-rules#481 treats exe/scr/com as executable extensions.
- **SmartScreen Experience field VALIDATED** this round: `parse_json(AdditionalFields).Experience`
  is the exact form used by community queries (jeffreyappel.nl SmartScreen writeup — values
  Untrusted/Phishing/Malicious/Exploit/CustomBlockList; reprise99/Sentinel-Queries uses
  AdditionalFields.Experience on the Sentinel backend where it's dynamic-typed).
- **No WmiPersistentEventSubscriptionCreated** exists (zero search hits) — the WMI leg is not
  missing a sibling.
- Runtime: parser check PASS; smoke run (tamper row → Loud rf=2 T1 B1 C0 DEFENDER_TAMPERING;
  driver row → Stable rf=1 DRIVER_LOADED regression intact; old-shape drops the new flag
  gracefully; single-row clean; invariant on every row). Artifacts deleted.
- Post-round sweep (same round): DeviceProcessEvents is ProcessCreated-ONLY today — a
  quoted search for `ActionType == "ProcessTerminated"` returns ZERO hits and
  azure/azure-sentinel#2750 states "ActionType will only be ProcessCreated for now" — the
  query's missing ActionType filter is correct (no termination-event inflation). The
  mandikgoyal/M365D_table repo (full action-type inventory in one README) has drift
  (lists "OpenProcess" under DeviceProcessEvents — it's a DeviceEvents type; 2023-era) —
  use it for cross-checks only, settle with primary evidence. What's-new (June 2026):
  AgentsInfo/AIAgentsInfo transition covers endpoint-discovered agents — the documented
  IsAITool overlap; no new endpoint exe-discovery tables/action types; the query's tables
  are untouched. Firecrawl MCP /extract is now DISABLED via
  mcp_servers.firecrawl.tools.exclude (raw tool name; globs supported; include beats
  exclude; takes effect next session) — the audit constraint is search/scrape/map/
  research_search_github only.

## v3.16 (round 15 — four dead persistence joins + case-drift class; all MCP-verified)

- **THE JOIN-GROUPING TRAP (biggest find of the round)**: after `join` where the RIGHT side also
  carries a column that exists on the LEFT, Kusto renames the right side's duplicate with a
  `1` suffix (`Key` → `Key1`, `FileName` → `FileName1` — join-inner docs example output:
  `Key | Value1 | Key1 | Value2`). A bare `by SHA1` after such a join therefore binds to the
  LEFT side's SHA1. Consequence in the query: schtasks + Register-ScheduledTask legs grouped
  by schtasks.exe/powershell.exe's OWN hash; ScheduledTaskCreated by DeviceEvents.SHA1
  (no file → null); SelfDeletes by the deleted file's hash. The first three could NEVER
  match any candidate (dead legs, silently empty columns); SelfDeletes only fired for
  byte-identical self-copies. Fix: rename the right side explicitly in the project
  (`CandidateSHA1 = SHA1, CandidateFileName = FileName`) and group `by SHA1 = CandidateSHA1`.
  Pattern to use everywhere from now on.
- **Case-drift class**: filename joins (Run keys, schtasks legs, self-delete name compare) and
  registry value-name comparisons used case-sensitive `==`/`in` on a case-insensitive
  filesystem/registry. Fixed with tolower() both sides for joins (docs: join on-clause
  documents only `==`; community workaround is tolower) and `=~`/`in~` for value comparisons.
  IMPORTANT (MS docs, in-operator page): "Case-insensitive operators are currently supported
  only for ASCII-text. For non-ASCII comparison, use the tolower() function." → vendor joins
  (PE CompanyName vs TVM SoftwareVendor) MUST use tolower, not =~.
- **NonStandardPorts null guard**: `array_length(set_difference(TopDestPorts, StandardPorts)) > 0`
  with null TopDestPorts (rows without network events) evaluates to null; `isnotnull(...) and ...`
  is provably semantics-preserving (false dominates under both 2VL and 3VL null handling).
- **Verified this round (cite these)**: FileProfile(SHA1, 1000) — second param IS a record cap
  ("y — limit to the number of records to enrich, 1-1000; function uses 100 if unspecified";
  ProfileAvailability description mentions "the maximum number of files was reached") → the
  header's "1000-file cap" claim is correct, not a time window. Join suffix convention: the
  earlier "_1" answer from an extractor was WRONG — the docs example shows "1". DeviceEvents
  30-day retention (xdrinternals HotDays=30). Official MS scheduled-task query
  (Microsoft-365-Defender-Hunting-Queries/Persistence/scheduled task creation.txt) uses
  `DeviceEvents | where ActionType == "ScheduledTaskCreated"` — verbatim match for the leg.
  Self-deletion precedent: elastic/detection-rules#481 correlates deletion by name/path, not
  hash. ServiceInstalled = event 4697, gated on the "Security System Extension" audit
  subcategory (ultimatewindowssecurity event-4697; spiceworks confirmations).
- **PS1**: both Import-Csv calls now `-Encoding UTF8` — PS 5.1 Import-Csv defaults to ANSI;
  a UTF-8 no-BOM export would mojibake non-ASCII names/companies (BOM'd exports were already
  handled by BOM detection). No flag changes.
- Runtime: parser check PASS; smoke run (3-row UTF-8 incl. non-ASCII company, old-shape,
  single-row) — T+B+C==rf on every row, redflagged.csv = Loud+RedFlagged only, non-ASCII
  round-trip intact, empty-input edge graceful.

## v3.15 (round 14 — three query-fatal bugs + actor-behavior expansion; all MCP-verified)

- **Drive-letter regex was a compile error**: `FolderPath matches regex @"^[D-Z]:\"` (one trailing backslash) is RE2-invalid — Kusto's regex is the RE2 family and a trailing backslash fails compilation (ClickHouse/RE2 evidence: posthog#58706; Kusto regex page). Fix: `@"^[D-Z]:\\"` (two backslashes = regex escape for one literal backslash). Byte-verified in the file (L178/L197). The query had never run in the portal — all 8 prior audits were static, so this class survived.
- **Branch-2 FileProfile collision**: branch 2 joined CertInfo (incl. Signer) then invoked `FileProfile(SHA1, 1000)` — FileProfile's documented output includes Signer (MS Learn fileprofile-function page), invoke appends the function schema to the input, and duplicate column names are impossible in a Kusto tabular schema (no rename mechanism) → query error at that step. Branch 1 had the correct project-away; branch 2 (added later) didn't. Fix: `| extend CertSigner = Signer | project-away Signer` before invoke; IsInternalTool now matches Signer OR CertSigner (cert signer is the fallback for rows past the 1000-file cap).
- **Phantom `RemoteIPIsPrivate`**: the v3.7 raw-IP countif referenced a column that does NOT exist in DeviceNetworkEvents (absent from the MS Learn schema page and the xdrinternals in-portal mirror; a Reddit analyst derives it via `ipv4_is_private(RemoteIP)` — computed, not schema). Fix: `RemoteIPType == "Public"` (documented enum: Public/Private/Reserved/Loopback/Teredo/FourToSixMapping/Broadcast). The skill's "column verified in the schema" claim from v3.7 was WRONG — corrected.
- **TvmFileEvidence joins**: (a) case-sensitive match against a lowercased right side → silent misses on Windows case drift; fix: `extend TopFolderLower = tolower(TopFolderPath)` + join on it (both branches). (b) `hint.shufflekey = SHA1` where SHA1 is not a join key and absent from the right side — docs require the shuffle key to be a join key; removed (hints never change semantics, so removal is provably safe).
- **UserCount was dcount(DistinctUsers)** — dcount over the per-device dcount VALUES (meaningless). Now `sum(DistinctUsers)` = user-device pairs, an honest upper bound on distinct users (display-only column; no decision impact). Comment documents it.
- **ActorBehaviorEvents expanded** (all types verified in the current 184-type DeviceEvents inventory via xdrinternals): ProcessTamperingHits now covers the full T1055 remote-memory family (CreateRemoteThreadApiCall, QueueUserApcRemoteApiCall, SetThreadContextRemoteApiCall, NtAllocateVirtualMemoryRemoteApiCall, NtMapViewOfSectionRemoteApiCall, MemoryRemoteProtect) and a new `DriverLoads` column (candidate loaded a kernel driver — Splunk "Windows Driver Load Non-Standard Path" analytic validates the hunting value). PS1: DRIVER_LOADED red+1/Behavior/NOT loud — a signed+prevalent driver-loading tool stays Stable (same reasoning as SERVICE_INSTALLED).
- **Rejected with reasons**: GetAsyncKeyStateApiCall (keylogger API — no hunting-query precedent found, unquantified FP load on legit AutoHotkey/game/RMM tools), ScreenshotTaken/GetClipboardData (noise), LdapSearch (legit portable AD tools), AuditPolicyModification (attribution usually System), CredentialsBackup (ambiguous semantics).
- **Sanity-anchor drift (expected, not a bug)**: the v3.3 fixture's "payload lands rf=9 T2 B6 C1" predates SYSTEM_NAMED — the fixture's payload is literally named svchost.exe, so the CURRENT code yields rf=10 T2 B7 C1, still Loud. Renamed-LOLBin rows that were "RedFlagged" are now "Loud" (LoudSignal outranks RedFlagged since v3.1). Old anchor values in the skill's fixture docstring were updated.
- Regression harness for this round: 32-row v3.15-shape CSV covering every flag path (incl. DRIVER_LOADED both signed and unsigned), previous-run CSV (growth + decision carry-over), old-shape 37-col CSV, single-row CSV; assertions: T+B+C==rf on every row, per-row rf/families/loud/bucket, flag presence, redflagged.csv = Loud+RedFlagged only. RESULT: 251/251 checks passed (parser 0 errors; 65-row invariant sweep clean; payload row rf=10 T2 B7 C1 Loud; DRIVER_LOADED unsigned→RedFlagged rf=2, signed→Stable rf=1; old-shape CCC333 degrades rf=8 still Loud; single-row clean; redflagged.csv exactly 21 Loud+RedFlagged rows). Harness gotchas hit: in-process `&` invocation never sets $LASTEXITCODE (use try/catch), and a malware-hit fixture row that is unsigned gets UNSIGNED+MALWARE_HIT=rf=2, not rf=1.

## v3.14 (twelfth audit — DPAPI + native task events)

- `DpapiAccessed` added to ActorBehaviorEvents (T1555.004 — DPAPI-secret decryption; DPAPI_ACCESS red+loud). Found via the full-inventory sweep: the 223-type list contains DpapiAccessed, ScheduledTaskCreated/Updated/Deleted/Enabled/Disabled, SensitiveFileRead, OpenProcessApiCall etc. — grep the saved inventory for unused-but-relevant names each audit round.
- `ScheduledTaskCreated` (native DeviceEvents) added to persistence — method-independent task creation (COM/.NET TaskService paths that schtasks-CLI parsing misses).
- Verified: creddump.exe with 4 DPAPI accesses → Loud rf=3.

## Rounds 7–13 (exhaustion audit — user: "don't stop until multiple different searches find nothing")

- Method: batches of 3 independent searches per round; implement what verifies; stop after 2+ CONSECUTIVE batches with nothing implementable (batches 12–13 were the empty pair; every find in the run-up was externally validated before implementation).
- Finds beyond v3.11–v3.14 above: SYSTEM_NAMED (copied system binary keeps OriginalFileName so RENAMED never fires — name-in-user-path IS the signal; from the techjack ClickOnce hunting set; red+loud), SEARCH_ORDER_HIJACK (system-named DLL in candidate folder — PS1-side check of SideloadedUnsignedDlls against a ~28-name list: version.dll/winmm.dll/ws2_32.dll/bcrypt.dll/amsi.dll...; red, not loud), DOUBLE_EXTENSION (`invoice.pdf.exe` with spoofed OriginalFileName defeats RENAMED; explicit extension-list regex, flag-only, no FP on 7zsetup-x64.exe — verified).
- Validated-not-implemented: Elastic new_terms first-seen ≈ radar branch; official FileCreatedInStartupFolder ≈ v3.6 startup LNKs; RoguePlanet hunts use `ProcessIntegrityLevel == "System"` (validates ELEVATED); MS official PUA doc shows `AntivirusDetection` + `AdditionalFields.ThreatName startswith 'PUA:'` (validates v3.10); AppControlScriptAudited (ETW 8006) closes the script gap IF user-mode WDAC audit is ever enabled.
- Rejected with reasons: Defender GPO-path exclusion keys (not collected), RemovableStorageFileEvent (device-control-policy-gated), TLD flags (no precedent), USB-mount correlation (weak), FileOriginUrl "data:" URI (no precedent).
- Final scoreboard (13 rounds): ~22 gaps closed, 2 wrong claims corrected, 3 rejected with reasons, 1 verification-only round. Remaining gaps are structural: 30-day retention, COM hijacks, script tools (header has the reference material), WSL (separate Linux ecosystem), portal run.


## Reference: kusto-verification.md

# KQL claim-verification playbook (MDE AH queries)

## When
Before a query's first portal run — or after a review — when correctness depends on schema columns, operator semantics, retention, or join keys. Review alone is NOT enough; this audit class caught three real bugs in one pipeline (term-based `has` silently killing filters, phantom `contains_any` that would error, HKCU overclaim in comments).

## Workflow
1. **Enumerate load-bearing claims.** For the portable-app pipeline: every schema column referenced (18 checked), operator semantics (has/contains, contains_any existence, bool comparisons), behavior claims (HKCU registry coverage, AH retention, FileProfile cap).
2. **Schema columns → ONE firecrawl_extract** over the MS Learn schema pages:
   - urls: `learn.microsoft.com/en-us/defender-xdr/advanced-hunting-{deviceprocessevents,devicefileevents,identityinfo,devicetvmsoftwareinventory,alertevidence,devicenetworkevents}-table`
   - prompt: "For each page report whether each column exists (YES/NO + exact name): ..." — per-table structured answer; 18/18 confirmed in one call (~37 credits).
   - Note: the extract API warns `/v2/extract` is deprecated → `/v2/scrape` with a json format object; it still worked.
3. **Operator existence → firecrawl_map** with `search=` on `https://learn.microsoft.com/en-us/kusto/query/`:
   - Proves a doc page exists or NOT. Guessed URLs 404'd (`contains-anyoperator`, `contains-any-operator`); the map returned `has-any-operator` and NO contains_any page → operator doesn't exist. Don't guess URLs — map first.
4. **Operator semantics → scrape the authoritative pages**: `datatypes-string-operators` (full operator table + the term definition), `kql-quick-reference` (cheat sheet), individual operator pages (`has-operator`).
5. **Behavior claims** (HKCU capture, retention) → MS Learn official answers / schema docs over community blogs; Microsoft's own query repos (microsoft/Microsoft-365-Defender-Hunting-Queries) over third-party.
6. **Classify + fix + re-audit**: mark each claim confirmed / needs-fix / comment-only; after fixing, grep the file for the same bug class (e.g. `contains_any|has @"|has_any` with punctuated RHS).

## Findings table (2026-07-31, portable-app pipeline)

| Claim | Verdict | Source |
|---|---|---|
| SmartScreen ActionTypes `SmartScreenAppWarning`/`SmartScreenUserOverride` | ✓ confirmed | MS hunting-queries repo |
| `union` pads missing columns with nulls (default kind=outer) | ✓ confirmed | union-operator docs; check same-name-different-type → auto-suffixed `_type` |
| DeviceImageLoadEvents GA, collected by default | ✓ confirmed | schema docs |
| AH retention default 30 days | ✓ confirmed | advanced-hunting overview → creationLookback only matters if retention extended |
| IsSigned/IsTrusted are bool; compare with bool literals (`!= true or isnull(col)`) | ✓ confirmed | schema + df00tech/Kostas community idiom |
| parse_path property is `Filename` (capital F) | ✓ confirmed | parse-path docs |
| `invoke FileProfile(SHA1, 1000)`; 1000 cap; ProfileAvailability Available/Missing/Error/empty | ✓ confirmed | FileProfile docs |
| `has` is term-based; RHS with dots/backslashes/slashes never matches | ✓ confirmed | datatypes-string-operators (`"KustoExplorerQueryRun" has "Explorer"` → false) |
| `contains_any` exists | ✗ FALSE — does not exist | full operator table + quick reference + docs map (only has_any/has_all) |
| DeviceRegistryEvents captures HKCU | ✗ FALSE — HKLM only | MS answers /questions/3978033 |

## Fix patterns that survive verification
- Path substring → `contains`
- Multi-pattern substring → or-chain of `contains` | `matches regex @"(?i)alt1\\|alt2\\"` (double backslashes = literal `\`; `(?i)` = case-insensitive) | `has_any` only if every RHS is a plain word
- Dotted-filename join → `tostring(parse_path(X).Filename)` + `==` equality (whole-filename, also more precise)
- Bool column → `== true` / `!= true or isnull(col)` — never string "True"
- FileProfile → invoke PER BRANCH (cap is per-invoke; a big census branch starves a small radar branch otherwise)
- Comments: never claim coverage you can't see (HKCU); document retention bounds in the query header

## MCP outage fallback
The audit is backend-agnostic: when Exa MCP was down (hosted endpoint 404 on all paths), the built-in web_search backend carried the same queries without loss. If MCP tools return "Unknown tool" mid-session, the transport died and tools were unregistered — fix the server, then `/reload-mcp`. See the `mcp-server-diagnostics` skill.


## Reference: deviceevents-actiontypes.md

# DeviceEvents ActionType inventory — verified bank (2026-07-31, external-audit pass 3)

## How to get the authoritative ActionType list
- MS Learn (`advanced-hunting-deviceevents-table`) describes only the table's COLUMNS; the
  ActionType VALUES are in the in-portal schema reference (no public URL).
- Community mirror with the full 223-type list per table:
  `https://xdrinternals.com/docs/microsoftxdr/devices/deviceevents/` (and sibling paths for
  other AH tables: deviceregistryevents, deviceprocessevents, ...).
- Firecrawl-scrape gotcha: xdrinternals returns the page as a JSON-ESCAPED string inside the
  tool result. `json.loads(raw)` then `data["result"]` may itself be a string needing a
  second `json.loads` before `.find("## Action types")` works. The earlier `data["result"]["markdown"]`
  one-shot failed with "string indices must be integers" — that was the single-parse bug, not the site.

## Verified ActionTypes relevant to portable-app / persistence / trust work
All names verified VERBATIM against the inventory (v3.6 query uses exactly these):

| ActionType | Meaning | Audit gating |
|---|---|---|
| `ServiceInstalled` | Service installed (Win event 4697) | Requires "Audit Security System Extension" — inert in tenants without it |
| `WmiBindEventFilterToConsumer` | WMI event filter bound to consumer = WMI persistence created | Audit-INDEPENDENT |
| `ProcessCreatedUsingWmiQuery` | A process was created via WMI | Audit-INDEPENDENT |
| `RemoteWmiOperation` | WMI operation initiated from a remote device | (schema ambiguity — SHA1 may not be the created process; not used) |
| `AsrUntrustedExecutableAudited/Blocked` | Rule 01443614 — prevalence/age/trusted-list verdict | ASR rule deployment |
| `AsrUntrustedUsbProcessAudited/Blocked` | Rule b2b3f03d — untrusted/unsigned from USB | ASR rule deployment |
| `AsrPsexecWmiChildProcessAudited/Blocked` | Rule d1e49aac — process created via PsExec/WMI | ASR rule deployment |
| `AsrAbusedSystemToolAudited/Blocked` | Rule 56a46372 — copied/impersonated system tool (MS's verdict for the renamed-LOLBin pattern) | ASR rule deployment |
| `AsrPersistenceThroughWmiAudited/Blocked` | Rule 92e97fa1 — persistence via WMI event subscription | ASR rule deployment |
| `AppControlExecutableAudited/Blocked`, `AppControlScriptAudited/Blocked`, `AppControlAppInstallation*` | WDAC/AppLocker untrusted file/script events | WDAC user-mode policies — dormant with kernel-drivers+CLM-only policies |
| `DriverLoad` | Driver loaded | — |
| `AsrObfuscatedScript*`, `AsrScriptExecutableDownload*` | Script-obfuscation / JS-VBS-launching-download verdicts | ASR rule deployment |

Also confirmed in the inventory: `AsrRansomware*`, `AsrVulnerableSignedDriver*`, `AsrOfficeChildProcess*`,
`AsrOfficeProcessInjection*`, `AntivirusDetection` etc. — the full ASR family is queryable by rule.

## What pass 3 changed in the pipeline (v3.6)
1. Persistence widened: services + WMI subscriptions + startup-folder LNKs (previously documented
   "not visible" — wrong on all three):
   - `PersistenceEvents` let: `DeviceEvents | where ActionType in ("ServiceInstalled","WmiBindEventFilterToConsumer")`
     → `ServicesInstalled`, `WmiPersistenceHits` per candidate SHA1.
   - `StartupFiles` let: `DeviceFileEvents | where ActionType == "FileCreated" | where FolderPath contains @"\Startup\"`
     → `StartupFilesCreated`.
2. `AsrAuditEvents` extended with AsrAbusedSystemTool* + AsrPersistenceThroughWmi* (4 rule families
   now feed `AsrUntrustedHits`; PS1 flag renamed ASR_UNTRUSTED → ASR_VERDICT).
3. `PsexecWmiEvents` extended with `ProcessCreatedUsingWmiQuery` (remote-launch signal works even
   without ASR rule d1e49aac deployed).
4. HKCU claim corrected: community runbooks query HKCU paths in DeviceRegistryEvents directly
   (Crimson7research runbook: `RegistryKey has_any "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion..."`;
   forenza.io: per-user `HKEY_CURRENT_USER\Software\Classes\CLSID` COM-hijack hunts). The run-key
   filter `contains @"\CurrentVersion\Run"` matches either hive. Never state "HKLM only" without
   re-checking community usage.

## PS1 flag semantics chosen for the new signals (verified by 4-row regression)
- SERVICE_INSTALLED: red (+1), Behavior family, NOT loud — signed service-installing tool stays Stable.
- WMI_PERSISTENCE: red (+1), Behavior, loud (persistence mechanism, same class as PERSISTENCE).
- STARTUP_LNK: red (+1), Behavior, loud.
- One red per MECHANISM (run-key app + service = PERSISTENCE + SERVICE_INSTALLED = 2 reds).
- T+B+C==RedFlagCount invariant re-verified after every patch (a dropped `$c++` broke it silently once).

## Other confirmed facts from pass 3
- Microsoft's official hunting-query repo moved: microsoft/Microsoft-365-Defender-Hunting-Queries is
  DEPRECATED → Azure/Azure-Sentinel "Hunting Queries/Microsoft 365 Defender".
- Splunk's RMM analytic pattern: RMM install/service registration + first outbound connection to
  vendor cloud within 1h — the network half of RMM governance (portable-app discovery covers the file half).
- Elastic detection-rules PR #5592 is the canonical source for the sideload subdirectory-evasion fix
  (startswith vs endswith directory matching; Downloads added to suspicious path list).
- WDAC `AppControlScriptAudited/Blocked` = untrusted SCRIPT events: the script-tools gap
  (powershell -File from user folders) is closable via platform signals if user-mode WDAC policies
  are ever deployed — 6-line join behind a knob, same shape as AsrAuditEvents.

## Passes 9–12 additions (v3.11–v3.14) — actor-behavior family + native task events

**CRITICAL JOIN RULE**: for actor-behavior events the event's own `SHA1` is the TARGET file/process
(SensitiveFileRead: the ssh key read; OpenProcessApiCall: the process opened). The candidate is
`InitiatingProcessSHA1`. Join on the ACTOR hash or nothing ever matches. (ASR verdict events are the
opposite — their SHA1 IS the untrusted executable; keep those on SHA1.)

| ActionType | Meaning | Usage in pipeline |
|---|---|---|
| `SensitiveFileRead` | Process read sensitive files (ssh keys, Outlook archives) | SENSITIVE_READ red+loud |
| `DpapiAccessed` | DPAPI-protected secrets decrypted (T1555.004) | DPAPI_ACCESS red+loud |
| `OpenProcessApiCall` / `ReadProcessMemoryApiCall` | Process-open / memory-read APIs (injection primitives) | TAMPERING_APIS red (not loud) |
| `WriteToLsassProcessMemory` | Write to lsass memory (credential theft) | TAMPERING_APIS red |
| `ProcessPrimaryTokenModified` | Primary token modified (privilege/impersonation) | TAMPERING_APIS red |
| `FileTimestampModificationEvent` | File timestamp modified (T1070.006 timestomping) | TIMESTOMP flag-only (extractors/backups restore timestamps) |
| `ShellLinkCreateFileEvent` | .lnk file created (MS Learn Q&A-validated; Chronicle maps to FILE_CREATION) | SHELL_LINK_CREATION flag-only |
| `ScheduledTaskCreated` / `ScheduledTaskUpdated` / `ScheduledTaskDeleted` / `ScheduledTaskEnabled` / `ScheduledTaskDisabled` | Native task-scheduler events — METHOD-INDEPENDENT (catches COM/.NET TaskService creation that schtasks-CLI parsing misses) | ScheduledTaskCreated feeds PersistenceDetected |
| `AsrScriptExecutableDownloadAudited/Blocked` | JS/VBS launching downloaded executable content | Added to AsrAuditEvents (v3.11) |

Audit-gating notes: none of the actor-behavior types require extra audit settings (unlike
ServiceInstalled/4697); the ASR families require rule deployment. `AmsiScriptDetection` exists in
DeviceEvents + AH (kqlquery.com timeline-internals table) — script-artifact telemetry, not used by
the exe census.

Verified dead-ends from the exhaustion passes (do NOT rebuild):
- Defender-exclusion tampering: the GPO-path key `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Exclusions`
  is NOT collected in AH (cloudbrothers.info research — "you will not find any changes... in the
  advanced hunting data"); the monitored non-policy key is locked down. No registry join can detect it.
- `RemovableStorageFileEvent` / `RemovableStoragePolicyTriggered`: fire ONLY when Device Control
  policies are configured — no policies, no events. Policy-gated, not a discovery signal.
- `RemoteWmiOperation`: schema ambiguity (SHA1 may not be the created process) — use
  `ProcessCreatedUsingWmiQuery` instead.
- kqlsearch.com search route 404s (`/search?q=`) — query pages work (`/query/<name>&<id>`), search doesn't.
