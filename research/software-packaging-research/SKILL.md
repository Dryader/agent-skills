---
name: software-packaging-research
description: Use when asked how software installs or updates itself.
---


# Software Packaging Research

Questions like "does it patch itself when updating, or reinstall?" or "when is JAVA_HOME set?" cannot be answered from memory. Behavior differs by packaging format (Windows MSI vs deb/rpm vs macOS pkg vs zip/archive) and changes between releases. Read the primary sources every time, and quote exact identifiers (folder patterns, feature IDs, upgrade rules) in the answer.

## Source ladder, in order

1. **Official installation docs**, per-platform page. Gives default install location, default features, documented upgrade rules. Docs describe intent and lag reality.
2. **Upstream support issue tracker** (repo Issues). Search: "update", "upgrade", "install path", "auto update", "old version". Maintainer replies are authoritative and often more accurate than docs; user reports reveal edge cases (locked files during upgrade, leftover folders, env vars pointing at stale paths).
3. **Packaging source** in the upstream repo. Settles remaining ambiguity: default install directory, feature list with levels/defaults, which env vars get written under what conditions, upgrade scheduling. Typical layout: `wix/` (Windows), `pkgbuild/` (macOS), `linux/` (deb/rpm).

Never answer from blogs/forum posts when 1-3 are reachable.

## Question-to-source map

| Question | Answer lives in |
|---|---|
| Does it auto-update? | Tracker; assume NO for open-source unless a maintainer says otherwise. |
| Patch in place vs full reinstall? | Packaging source. Almost always: every release is a complete build, no delta patches. The real difference is whether the full replacement lands at the same path or a new versioned path. |
| Where do files land after an update? | Installer source: the folder-name template (full version in path, or feature version only?). |
| What does install option X set? | Feature table / component conditions in the installer source. |
| When is env var Y set? | Component conditions + defaults: opt-in or not, user vs system scope, behavior on upgrade and uninstall. |
| What breaks after an update? | Anything hardcoded to a versioned path; manually set env vars; services with stale paths. |

## Reading package source from GitHub (recipe)

- List a directory as JSON (works through web_extract): `https://api.github.com/repos/<org>/<repo>/contents/<dir>`
- Download raw files to a scratch dir, then read/grep locally: `curl -sL -o out.file https://raw.githubusercontent.com/<org>/<repo>/<branch>/<path>`. Rendered page extraction strips markup from XML/WiX/code, so take the raw file for anything syntax-sensitive.
- Grep for: `INSTALLDIR`, `AppFolder`, `Environment`, `Feature`, `Level=`, `Upgrade`, `RemoveExistingProducts`, `ProductVersion`.
- Installer variables like `ProgramFiles64Folder` or `LocalAppDataFolder` must be resolved to real paths before answering.

## Answer shape

- Verdict first ("No, it never patches itself"), then a compact per-platform table, then the operational takeaway for the user's own machine.
- Quote exact paths/patterns from source (`jdk-<ProductVersion>-hotspot` → `jdk-11.0.22.7-hotspot`), not paraphrases. Precise attribution beats hedging.
- For "when is X set" questions cover the full surface: default state, opt-in path (exact feature ID, checkbox label, or command-line flag), scope (system vs user), timing, behavior on update, behavior on uninstall.
- Close with what to do so updates don't break them (fixed install dir, let the installer manage env vars, what to verify after each upgrade).

## Pitfalls

- "Patch release" does not mean patching: quarterly security releases are full builds; the download is the entire package.
- Same product, different formats, different behavior: Windows MSIs commonly install each release into a NEW versioned folder; Linux/macOS packages replace in place at a stable feature-version path. Answer per platform, never with one blanket claim.
- Windows MSI major upgrades uninstall the previous same-major install as part of the transaction; cross-major versions (11 vs 17) stay side by side by design. Documented upgrade-version rules (which version-field changes can upgrade) are worth quoting; running processes holding files can leave old-folder remnants.
- Optionally-supported env vars (JAVA_HOME-style) are typically NOT set by default installs. Check the feature's level/default in the source before claiming anything.
- Feature selections migrate across same-major upgrades, which is why "let the installer manage PATH/JAVA_HOME" survives versioned-path churn; a manually set variable is never touched and silently goes stale.
- Read support threads past the first message: the issue title often posits the wrong model ("turn off auto-update") and the maintainer's reply corrects it.

## References

- `Reference: temurin-jdk` — condensed Eclipse Temurin (Adoptium) packaging behavior: update model per format, install paths, MSI features, JAVA_HOME semantics.

## Reference: temurin-jdk

# Eclipse Temurin (Adoptium) packaging behavior

## Update model

- No auto-updater on any platform. The MSI, pkg, deb, and rpm contain no update logic (that is Oracle's Java Auto Updater, a different distribution). Temurin only updates when you run a new installer or the package manager/winget does.
- No delta patching: every release (quarterly plus out-of-band security releases) is a complete build; updating means downloading the whole thing (~100+ MB).
- Version mapping example: Java 11 update 11.0.22+7 -> MSI/dir version 11.0.22.7.

## Windows MSI

- Default root `C:\Program Files\Eclipse Adoptium\`, one folder per release: `jdk-<full version incl. build>-<jvm>` e.g. `jdk-11.0.22.7-hotspot` (source: `AppFolder = jdk-$(ProductVersion)-$(JVM)`). The path therefore changes on every patch release.
- Same-major upgrade (11.0.20.x -> 11.0.21.x): MSI major upgrade — new full copy into its new folder, previous install removed in the same transaction. Documented rule: upgrading works only when the first three version fields differ; a fourth-field-only change needs manual uninstall + install; major-version changes (11 -> 17) never upgrade, both stay installed (or remove the old one yourself).
- Locked files (a service or JVM running out of the old folder) can leave remnants of the old version behind.
- Per-user installs (`MSIINSTALLPERUSER=1`, per-machine is the default) install under `%LocalAppData%\Programs\` and touch user-scope env vars instead of system-scope.
- Features: `FeatureMain` (level 1); `FeatureEnvironment` "Modify PATH variable" (level 1, default); `FeatureJarFileRunWith` (level 1, default); `FeatureJavaHome` "Set or override JAVA_HOME variable" (level 2, NOT installed by default); `FeatureOracleJavaSoft` registry keys (level 2, not default).
- Silent variants: `INSTALLLEVEL=1` = the default trio; `INSTALLLEVEL=2` adds JAVA_HOME + JavaSoft keys; or pick explicitly: `msiexec /i <msi> ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJarFileRunWith,FeatureJavaHome /quiet`.
- JAVA_HOME semantics: value is the versioned folder (`...\jdk-11.0.22.7-hotspot`), written during the install transaction; system scope for per-machine installs, user scope for per-user installs. Non-permanent: uninstalling Temurin removes the value it set. On same-major upgrades with the feature installed, the new installer repoints JAVA_HOME to the new folder; if the feature was never installed, a hand-set JAVA_HOME is left alone and goes stale after every update.
- Stable-path options: pass a fixed `INSTALLDIR` at install time, or keep the env-var features enabled so they are repointed each upgrade. `winget upgrade EclipseAdoptium.Temurin.<major>.JDK` drives updates (manifests are community-maintained and can lag).

## Linux

- deb path `/usr/lib/jvm/temurin-<major>-jdk-amd64`; rpm path `/usr/lib/jvm/temurin-<major>-jdk`. Feature-version-only, so stable across patch releases; `apt`/`dnf` upgrade replaces the package contents in place (full replacement, not a patch). `update-alternatives` entries for java/javac are wired up automatically; the packages do not set JAVA_HOME.

## macOS

- `/Library/Java/JavaVirtualMachines/temurin-<major>.jdk` (bundle name from `<vendor>-<major>.jdk`). Each update installs a full new bundle over the same path; no JAVA_HOME handling.

## Quick answers

- "Does Temurin patch itself?" No updater, no deltas; every update is a full replacement. On Windows each release is effectively a fresh install into a new versioned folder.
- "Where should JAVA_HOME / IDE toolchains / services point?" Never at a versioned folder on Windows unless the installer manages it (feature enabled) or a fixed INSTALLDIR was used. Verify with a fresh shell (`echo %JAVA_HOME%`) after each install or upgrade.
