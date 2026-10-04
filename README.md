# agent-skills

Original, battle-tested agent skills in the open [Agent Skills](https://agentskills.io/specification) format (YAML frontmatter + markdown instructions, optional scripts). 33 skills, 74 files, 9 categories.

Built and exercised inside [Hermes Agent](https://hermes-agent.nousresearch.com) on a Windows/WSL host across real production work: Microsoft Defender advanced hunting (KQL), application control and allowlisting (WDAC, AppLocker, Intune EPM), endpoint and Windows security engineering, MCP server operations and fleet tuning, agent infrastructure and skill-library maintenance, financial data engineering, and document engineering.

Everything here is original work written from direct experience — no adaptations, no product documentation, no personal data. Supporting material lives inside each skill body (reference files were folded in); runnable code ships as `scripts/` beside its skill.

## Categories

| Category | Skills | Domain |
|---|---|---|
| enterprise-security | 5 | MDE KQL hunting, application control, Intune app management, vulnerability scanning, security decision documents |
| agent-infrastructure | 5 | MCP diagnostics and fleet tuning, agent memory and tool evaluation, editor integration |
| meta | 6 | skill-library maintenance, skills-repo auditing, prompt auditing, pack import, skill slimming |
| research | 6 | cited briefs, devil's-advocate validation, OSINT person verification, search API and engine routing, software packaging |
| endpoint-engineering | 3 | Windows security & privacy hardening, browser privacy, WSL interop |
| github | 3 | Actions workflows, PR review, open-source contribution |
| documents | 2 | python-docx, OCR and document extraction |
| dev-workflow | 2 | subagent debate, adversarial audit lifecycle |
| finance | 1 | Financial data APIs (EDGAR, EODHD, Koyfin) |

See [SKILLS.md](SKILLS.md) for the full registry with descriptions.

## Install

Skills follow the `agentskills.io` layout, so they install into any compatible agent — copy a skill directory into your agent's skills folder:

```bash
cp -r enterprise-security/mde-advanced-hunting ~/.hermes/skills/   # Hermes
cp -r enterprise-security/mde-advanced-hunting ~/.claude/skills/   # Claude
cp -r enterprise-security/mde-advanced-hunting ~/.agents/skills/   # any agentskills.io-compatible agent
```

Scripts are optional; each skill documents its script dependencies in its body.

## Contributing

[AGENTS.md](AGENTS.md) defines the conventions: the frontmatter dialect (name + description + optional tags/triggers/related_skills — no author/version/license fields), the single-file skill rule, the original-work-only policy, the placeholder convention for personal data, and the validation commands to run before committing. The repo is MIT-licensed; attribution lives in the repo identity.

## Notes

- **The repo validates itself.** `scripts/validate_skills.py` runs the frontmatter, dangling-path, PII and count checks below and exits non-zero on failure; `.github/workflows/validate.yml` runs it on every push and pull request.
- Some skills reference bundled platform skills (`powerpoint`, `docx`, `arxiv`, and others) that install with the agent itself.
- Personal identifiers were removed from this public copy. Some scripts and references still contain live-environment paths (`~/portfolio_audit/...`, `~/.hermes/...`, `C:\Users\<user>\...`); they document the workflow the skill was built against, not portable paths.
- Skills use placeholder tokens (`[employer]`, `[institution]`, `<user>`) where specific names belong.

## License

MIT — see [LICENSE](LICENSE).
