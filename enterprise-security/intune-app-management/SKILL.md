---
name: intune-app-management
description: >
  Microsoft Intune application deployment, patching, and lifecycle management.
  Covers the three native app tracks (Enterprise App Catalog, Microsoft Store new,
  manual Win32), auto-update capabilities and limitations, supersedence, version
  sprawl handling, and the self-service app patching gap. Use when discussing
  Intune app deployment strategy, third-party app patching, or choosing between
  EAM / Store / Win32 deployment methods.
triggers:
  - Intune app deployment
  - Intune app patching
  - Enterprise App Catalog
  - EAM auto-update
  - Microsoft Store app (new)
  - Intune supersedence
  - Intune Win32 app
  - third-party app updates Intune
  - Intune application lifecycle
  - Notepad++ Intune
  - self-service apps Intune
  - version sprawl Intune
tags: [microsoft-365, intune, endpoint, security, windows]
---

# Intune App Management

## The Three Native App Tracks

Intune has three completely separate app deployment mechanisms. They serve different purposes and have different update behaviors. Conflating them leads to bad recommendations.

### 1. Enterprise App Catalog (EAM)
- **App type in Intune:** "Windows catalog app (Win32)" (under "Other" section)
- **Catalog:** Microsoft-curated, ~1,000+ pre-packaged Win32 apps, hosted by Microsoft
- **Installation:** Intune Management Extension (IME) — NOT winget
- **License:** EAM add-on, Intune Suite, or M365 E5 (as of July 2026)
- **Auto-update:** YES, but **Required assignments only**. Available apps must use guided supersedence.
- **Self-updating flag:** Some catalog apps are marked self-updating — Intune checks minimum version, app updates itself via vendor mechanism.
- **Good for:** Managed baseline apps (browsers, runtimes, VPN, security tools) — maybe 20-50 apps

### 2. Microsoft Store app (new)
- **App type in Intune:** "Microsoft Store app (new)" (under "Store app" section)
- **Catalog:** Microsoft Store — only apps publishers have actually submitted to the Store. NOT the full winget community repository.
- **Installation:** IME calls winget under the hood, but sources from the Store catalog
- **License:** Free (no EAM license needed)
- **Auto-update:** Yes, works for Available assignments. Intune keeps apps current.
- **Catalog size:** Much smaller than EAM. Many common Win32 apps are NOT in the Store (e.g., Notepad++, 7-Zip).
- **Good for:** Apps that happen to be in the Store and you want Available/self-service

### 3. Manual Win32 App
- **App type in Intune:** "Windows app (Win32)"
- **Catalog:** You package everything with Win32 Content Prep Tool
- **Installation:** IME
- **License:** Free
- **Auto-update:** No native auto-update. Must use supersedence (manual) or auto-update toggle on supersedence (Available only, two check-in delay, 8-16 hours).
- **Good for:** Apps not in EAM or Store, custom/LOB apps, or when you need full control

## Critical Distinction: Microsoft Store vs Winget Community Repo

**THIS IS THE #1 PITFALL.** These are different things:

| | Microsoft Store | Winget Community Repo |
|---|---|---|
| **What it is** | Curated app store, publisher-submitted | Community-maintained manifests on GitHub (`winget-pkgs`) |
| **Intune "Microsoft Store app (new)"** | Searches THIS catalog | Does NOT search this |
| **`winget install` CLI** | Can use `--source msstore` | Default source, much larger |
| **Notepad++?** | NO (dev refuses Store) | YES (`Notepad++.Notepad++`) |
| **7-Zip?** | Probably not | YES |

The Intune "Microsoft Store app (new)" type searches only the Microsoft Store catalog, not the full winget community repository. Apps must be submitted by their publisher to the Store to appear. Many common enterprise apps are missing.

## Auto-Update Capabilities by Track

| | Required | Available |
|---|---|---|
| **EAM Catalog** | Auto-update (GA June 2026) | Guided supersedence only (manual) |
| **Microsoft Store (new)** | Auto-update | Auto-update |
| **Manual Win32** | Supersedence (manual) | Supersedence + auto-update toggle |

### EAM Auto-Update Details
- GA as of Intune 2606 (June 2026)
- Enabled at app creation time — cannot flip existing apps from supersedence to auto-update
- No rollout rings — all targeted devices get the update simultaneously
- No rollback or automatic uninstall remediation
- No running-app detection — can force-close apps mid-use
- Cannot be used as blocking app in ESP/Autopilot

### Win32 Supersedence Auto-Update (Available Only)
- Separate feature from EAM auto-update
- Toggle "Auto-update" on the Available assignment of a superseding Win32 app
- Requires TWO device check-ins (8-16 hours total)
- **Critical caveat:** Only works if user originally installed from Company Portal. Pre-existing manual installs won't auto-update — no user consent tracking record.
- Max 10 superseding apps; max 11 nodes in supersedence graph

## Version Sprawl and Pre-Existing Installations

### EAM Catalog
- Detection rules recognize pre-existing installations → device shows "Installed" without forcing reinstall
- BUT auto-update is Required-only — if deployed as Available, no automatic patching
- Supersedence can target multiple old versions (one superseding app → many superseded, up to 10 nodes)

### Microsoft Store (new)
- Winget can detect SOME existing installations, but correlation is unreliable
- "Apps installed via MSI, EXE or older Win32 deployments may not be visible to WinGet"
- Available Store Win32 apps: user must manually install from Company Portal before Intune takes over
- For UWP apps: system-context assignment to device with existing install → error 0x87D1041C

### Manual Win32
- Detection rules are yours to write — full control but full responsibility
- Supersedence handles version sprawl by chaining old versions

## Self-Service App Patching: The Real Gap

Microsoft has not shipped a native, free solution for "keep hundreds of Available self-service Win32 apps patched across a fleet with version sprawl." This is an acknowledged architectural boundary.

### What Actually Works at Scale

**Tiered approach (most common):**
1. ~20-50 security-critical baseline apps → EAM Required + auto-update
2. Everything else → Available, accept patching gap, or use supplementary approach

**Winget DIY (free, self-maintained):**
- Package PowerShell scripts as Win32 apps that call `winget install`/`winget upgrade`
- Use proactive remediations for ongoing patching
- Projects: winget-intune-win32 (GitHub), IntuneGet (10,000+ apps, one-click deploy)
- Norwegian shop managing 400 apps: "If we can cut down 40-50% of our Win32 packages, that's a big win"

**Third-party tools (paid, automated):**
- Patch My PC, CapaOne Application Manager, ManageEngine Patch Connect Plus
- Integrate with Intune via Graph API
- Maintain catalogs of thousands of apps, auto-package updates, handle supersedence

### Microsoft's Official Position
From Microsoft Learn Q&A (April 2026): "Microsoft-native capabilities focus on system-managed app types... For extensive third-party app patching, a dedicated third-party tool integrated with Intune is often the most efficient solution."

## Research Verification Rules

When researching Intune capabilities:
- **Always check the catalog source** — Store vs winget community repo vs EAM catalog are three different things
- **Verify app availability** before recommending a track — Notepad++ is in EAM, not in Store
- **Check assignment type constraints** — auto-update capabilities differ dramatically by Required vs Available
- **The docs are fragmented** — EAM docs, Store docs, and Win32 supersedence docs are separate pages with overlapping but distinct information
- **Community blog posts often conflate tracks** — verify against official docs

## References

- intune-app-tracks-comparison.md — Detailed comparison of EAM, Store new, and manual Win32 tracks with sources


## Reference: intune-app-tracks-comparison.md

# Intune App Tracks — Detailed Comparison

## Quick Reference: Which Track for Which App?

| App | EAM Catalog | Store (new) | Manual Win32 |
|---|---|---|---|
| Notepad++ | Yes | No (dev refuses) | Yes |
| 7-Zip | Yes | Probably not | Yes |
| Google Chrome | Yes | Possibly | Yes |
| Firefox | Yes | Possibly | Yes |
| VLC | Yes | Probably not | Yes |
| GIMP | Yes | Unknown | Yes |
| Zoom | Yes | Possibly | Yes |
| Spotify | No | Yes (Store UWP) | Possible |
| WhatsApp | No | Yes (Store) | Possible |
| Custom LOB app | No | No | Yes |

## Auto-Update: The Full Matrix

### EAM Auto-Update (GA June 2026)
- **Assignment:** Required only
- **How it works:** Intune detects new catalog version → automatically pushes to all targeted devices. No new app object, no supersedence relationship.
- **Configuration:** Set at app creation time. Cannot flip existing apps from supersedence → auto-update.
- **Limitations:**
  - No rollout rings / phased deployment
  - No rollback or automatic uninstall remediation
  - No running-app detection (can force-close apps)
  - Cannot be ESP/Autopilot blocking app
  - Custom requirements, detection rules, install/uninstall scripts disabled
  - No version history per device in reporting
- **SLOs:** 80-90% of updates available within 24 hours of ingestion. Manual validation: up to 7 days.

### EAM Self-Updating Apps
- Some catalog apps are flagged as self-updating
- Intune checks minimum version only — app updates via vendor mechanism
- Intune reports detected version
- May need network rules to allow vendor update endpoints

### Microsoft Store (new) Auto-Update
- **Assignment:** Both Required and Available
- **How it works:** Intune keeps app current as new versions land in the Store
- **UWP apps:** Updated by the Store itself. Works even without Intune assignment once installed (unless Store policy blocks auto-update)
- **Win32 Store apps:** Updated by Intune. Must be assigned in Intune. Not affected by Store update policies.

### Win32 Supersedence Auto-Update (for Available)
- **Assignment:** Available for enrolled devices only
- **How it works:** Create supersedence relationship → toggle "Auto-update" on assignment → two device check-ins (8-16 hours) → update delivers
- **Key caveat:** Only works if user originally installed from Company Portal. Pre-existing manual installs have no user-consent tracking record and won't auto-update.
- **Retry:** Indefinite retry until user manually installs from Company Portal

## Version Sprawl Handling

### EAM Catalog Detection
- Pre-configured detection rules (file, registry, MSI product code)
- Recognizes pre-existing installations → device shows "Installed" (no forced reinstall)
- Detection rule must match the installed version. Non-standard install paths or very old versions may not match.

### Winget Correlation (Store new)
- Winget maps installed apps to package IDs using: MSI product codes, registry entries, file metadata
- **Reliability varies by app and install method**
- Known issue: `winget upgrade --id` can return "No installed package found" even when app is present
- GitHub issue #5688: tracking catalog missing product codes for some packages
- Community workaround: `winget install --id` can sometimes work where `winget upgrade` fails

### Manual Win32 Detection
- Full control: MSI product code, file version, registry, custom PowerShell script
- Version-aware detection (e.g., "file version >= X.Y.Z") prevents reinstall loops
- Common pitfall: detection rule too strict → app shows "not installed" after successful install → error 0x87D1041C

## The Self-Service Patching Gap — Direct Quotes

From CapaOne (April 2026):
> "Intune manages Windows updates through Windows Update for Business. It handles Microsoft applications through its native tooling. What it does not provide, out of the box, is an automated catalog for third-party applications. This is not a failure of Intune. It is a deliberate architectural boundary."

From Microsoft Learn Q&A (April 2026):
> "Microsoft-native capabilities focus on system-managed app types (Win32, MSIX, Store apps) rather than arbitrary per-user installs."

From Modern-Managed.com (Dec 2024):
> "One pitfall to avoid is making all apps required... Consider deploying only essential apps as required and using Available for Install for non-critical apps."

From CIAOPS (May 2025):
> "For extensive third-party app patching, a dedicated third-party tool integrated with Intune is often the most efficient solution."

From Norwegian shop managing 400 apps (Aug 2025):
> "It's not about 100% automation — it's about reducing the number of apps we manually manage. If we can cut down 40-50% of our Win32 packages, that's a big win."

From Jannik Reinhard on EAM auto-update (July 2026):
> "For standard tools like 7-Zip, Notepad++ or VLC-style utilities, Enterprise App Management auto-update is a clear win. These apps have frequent security updates, and nobody wants to build supersedence chains for them."

## Winget DIY Pattern

Common approach for apps not in EAM or Store:

1. Package PowerShell script as Win32 app
2. Install command: `pwsh.exe -MTA -File install.ps1` which calls `winget install --id Notepad++.Notepad++`
3. Detection script checks installed version via `Get-WinGetPackage`
4. Version = 'Latest' means detection script checks for updates each cycle
5. For ongoing patching: proactive remediation script runs `winget upgrade` on schedule

**Caveats:**
- WinGet.Client cmdlets don't work as SYSTEM in PowerShell v5 (need v7 + -MTA)
- SYSTEM context can cause failures for user-context apps
- No staging/rollout rings
- Apps running during upgrade may fail or corrupt

## Sources

- Microsoft Learn: Enterprise App Management overview
- Microsoft Learn: Add Microsoft Store apps to Intune
- Microsoft Learn: Guided update supersedence
- Microsoft Learn: Configure Win32 supersedence
- Tiago Carvalho: Enterprise App Catalog in Intune (March 2026)
- Jannik Reinhard: EAM Auto-Update Guide (July 2026)
- Thomas Marcussen: Auto-Updating Enterprise App Catalog Apps (July 2026)
- EndpointWeekly: Microsoft Store Apps in Intune (June 2026)
- Almenning Data: Modern App Management with Intune and WinGet (Aug 2025)
- SysOpsInsiders: Enterprise App Catalog Licensing and Auto-Update (July 2026)
