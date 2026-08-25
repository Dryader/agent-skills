# Skills

Index of the 22 skills in this repository, grouped by category. Each skill is a single self-contained `SKILL.md` in the open [Agent Skills](https://agentskills.io/specification) format, optionally accompanied by runnable scripts.

## agent-infrastructure (4)

- **agent-editor-integration** — Wire Hermes to editors/IDEs: direction, endpoints, security.
- **agent-memory-evaluation** — Should an agent get external memory (Hindsight/cognee/Zep)?
- **agent-tool-evaluation** — Use when the user asks if a tool or system is worth adding.
- **mcp-server-diagnostics** — Diagnose MCP server connection failures (especially hosted endpoints), choose the right endpoint + auth variant, and distinguish server outage from config error. Covers Hermes MCP client mechanics (hermes mcp list/test/login, /reload-mcp), raw HTTP endpoint probing, and known hosted-provider endpoint matrices (Firecrawl, Exa).

## dev-workflow (1)

- **subagent-debate** — Decision-making pattern using opposing subagent advocates. Each advocate researches and argues their position, then the parent agent judges based on evidence. Use for technology comparisons, architecture decisions, vendor evaluations, and any choice where both sides have merit.

## documents (2)

- **ocr-and-documents** — Extract text from PDFs/scans (pymupdf, marker-pdf).
- **python-docx** — Read, edit, and create .docx Word documents programmatically with python-docx. Covers text manipulation, formatting preservation, hyperlink handling, and document restructuring.

## endpoint-engineering (3)

- **browser-privacy-hardening** — Harden Firefox (and Chromium-based) browsers for privacy: about:config prefetch/network prefs, uBlock Origin interaction bugs, DNS-over-HTTPS layering (Firefox TRR vs OS-level), ECH, Early Hints bypass, arkenfox alignment. Use when the user asks about browser privacy settings, prefetching, DNS leaks past adblockers, about:config hardening, or DoH/DoT setup.
- **windows-security-privacy-optimization** — Windows 11 security features, privacy hardening, and gaming performance optimization. Covers VBS/HVCI, LSA, SAC/WDAC, telemetry, privacy registry keys, BIOS settings, and the security-vs-performance tradeoffs for home office + gaming PCs.
- **wsl-windows-interop** — WSL-Windows interop: paths, exes, GUI-stdio, MCP wiring.

## enterprise-security (5)

- **enterprise-application-control** — Enterprise application control and privilege management — WDAC, AppLocker, CyberArk EPM, Intune EPM, Santa (macOS). Covers allowlisting, portable app control, managed installer, per-user rules, and privilege management across Windows clients, servers, and macOS. Use when discussing application allowlisting, blocking portable/non-admin-installed apps, WDAC vs AppLocker, or endpoint privilege management in enterprise environments.
- **enterprise-comparison-documents** — Create multi-format enterprise technology comparison and recommendation documents (markdown + PowerPoint). Covers research methodology, document structure, depth calibration, and iteration workflow. For any task involving "compare X vs Y vs Z", "recommend a solution for", "write a strategy doc for", or "create a presentation about" enterprise technology decisions.
- **intune-app-management** — Microsoft Intune application deployment, patching, and lifecycle management. Covers the three native app tracks (Enterprise App Catalog, Microsoft Store new, manual Win32), auto-update capabilities and limitations, supersedence, version sprawl handling, and the self-service app patching gap. Use when discussing Intune app deployment strategy, third-party app patching, or choosing between EAM / Store / Win32 deployment methods.
- **mde-advanced-hunting** — Write, audit, and fix Microsoft Defender Advanced Hunting (MDE AH) KQL queries and the PowerShell pipelines that consume their CSV exports. Schema gotchas (parse_path, bool cert columns, FileProfile collisions), join semantics, and producer/consumer contract testing.
- **windows-vulnerability-scanning** — Use when researching Windows vulnerability scanning tools.

## finance (1)

- **financial-data-apis** — Select, compare, and use financial market data APIs for portfolio analysis, screening, and backtesting. Covers free and paid tiers, pitfalls, TSX/international coverage gaps, and the optimal free stack.

## github (3)

- **github-actions** — Use when inspecting or fixing GitHub Actions workflows.
- **github-code-review** — Review PRs: diffs, inline comments via gh or REST.
- **open-source-contribution** — Evaluate open-source issues for contribution suitability — find easy wins, avoid design-intent traps, tier by certainty.

## research (3)

- **devils-advocate-research** — Validate recommendations by searching for complaints, and do investigative deep-research on people/orgs by cross-referencing multiple sources to find contradictions and test claims against actions.
- **osint-person-verification** — Verify a real person's identity and public footprint from a name plus anchor info — public/professional sources only, with an ethics gate. Covers name-collision disambiguation, cross-platform handle correlation, and platform-specific lookup recipes.
- **search-engine-routing** — Use for every web search task; route engines automatically.
