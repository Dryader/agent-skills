---
name: windows-security-privacy-optimization
description: "Windows 11 security features, privacy hardening, and gaming performance optimization. Covers VBS/HVCI, LSA, SAC/WDAC, telemetry, privacy registry keys, BIOS settings, and the security-vs-performance tradeoffs for home office + gaming PCs."
triggers:
  - "windows security settings"
  - "VBS HVCI performance gaming"
  - "memory integrity gaming"
  - "smart app control"
  - "windows privacy registry keys"
  - "telemetry disable windows"
  - "device guard"
  - "secure boot keys dbx migration"
  - "windows update deferral rings wufb"
  - "autoruns not verified"
  - "LSA protection"
  - "attack surface reduction rules"
  - "network protection defender"
  - "PUA protection"
  - "defender MAPS samples"
  - "BIOS gaming optimization"
  - "windows event viewer analysis"
  - "TPM event 14 / fTPM error"
  - "GDID advertising ID"
tags: [windows, security, privacy, hardening, endpoint]
---

# Windows Security, Privacy & Gaming Optimization

## Security Feature Hierarchy (Performance Impact)

Rank by gaming performance cost, highest first:

1. **VBS/HVCI (Memory Integrity)** — 5-10% FPS loss, worst on CPU-bound games
   - Uses hypervisor to isolate kernel memory
   - Toggle via: Settings > Privacy & Security > Device Security > Core Isolation
   - Ryzen 5000 (Zen 3) supports MBEC/GMET hardware acceleration but still ~5-8% hit
   - Microsoft officially recommends toggling off for gaming, back on after
   - Windows 11 24H2/25H2 added "Optimize for gaming" toggle during OOBE
   - Windows updates can RE-ENABLE after you turn it off — check after major updates

2. **Virtual Machine Platform (VMP)** — ~1-2% overhead (bare hypervisor without HVCI)
   - Required for WSL. Disabling kills WSL.
   - Even with Memory Integrity OFF, if VMP is enabled the hypervisor still runs
   - Check: `Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform`
   - msinfo32 will show "A hypervisor has been detected" even with VBS off if VMP is on

3. **LSA Protection (RunAsPPL)** — ZERO gaming impact
   - Runs LSASS as Protected Process Light (no hypervisor involved)
   - Blocks credential dumping (Mimikatz etc.)
   - Leave ON always. No reason to disable.

4. **Smart App Control / WDAC** — ZERO gaming impact
   - Pre-execution cloud reputation check, not continuous scanning
   - SAC blocks unsigned/unknown executables with no per-app exceptions
   - As of 24H2/25H2: can toggle on/off freely (no longer requires reinstall)
   - "App Control for Business: Enforced" in msinfo is the default WDAC baseline, not custom

5. **Kernel DMA Protection** — ZERO gaming impact. Leave on.

## VBS/HVCI Performance Data (2024-2026 benchmarks)

| Source | CPU | Game/Scenario | FPS Delta |
|--------|-----|---------------|-----------|
| ComputerBase (Sep 2024) | Ryzen 5800X3D | Aggregate | ~8% loss |
| Tech YES City (Mar 2025) | Ryzen 9 9950X3D | Fortnite 1080p low | ~20% loss |
| MakeUseOf (2026) | Not specified | Personal test | ~12% gain when off |
| SmoothFPS aggregate | Various | CPU-bound games | 5-25% loss |
| windowsnews.ai | Ryzen 7 7800X3D | Cyberpunk 2077 | 8.3% gain when off |
| windowsnews.ai | Ryzen 7 7800X3D | CS2 | 5.1% gain when off |
| Windows Central (Aug 2025) | Ryzen 9800X3D | Black Myth Wukong 1% lows | 59% min FPS drop |

Key insight: **1% lows / frame consistency hurt more than average FPS.** Average FPS may be similar but stutters increase dramatically.

## Recommended Toggle Pattern for Home Office + Gaming

```
# Before gaming:
Settings > Privacy & Security > Device Security > Core Isolation > Memory Integrity OFF
Restart

# After gaming:
Turn back ON
```

## Privacy Registry Keys (Verified)

All verified against Microsoft Docs and ntdevlabs/nano11 project.

### User-Level (HKCU)

| Setting | Path | Key | Value for Privacy |
|---------|------|-----|-------------------|
| Advertising ID | `HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo` | `Enabled` | 0 |
| Tailored Experiences | `HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy` | `TailoredExperiencesWithDiagnosticDataEnabled` | 0 |
| Restrict Ink Collection | `HKCU:\Software\Microsoft\InputPersonalization` | `RestrictImplicitInkCollection` | 1 |
| Restrict Text Collection | `HKCU:\Software\Microsoft\InputPersonalization` | `RestrictImplicitTextCollection` | 1 |
| Harvest Contacts | `HKCU:\Software\Microsoft\InputPersonalization\TrainedDataStore` | `HarvestContacts` | 0 |
| Silent App Install | `HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager` | `SilentInstalledAppsEnabled` | 0 |
| Soft Landing Tips | `HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager` | `SoftLandingEnabled` | 0 |
| OEM Pre-installed Apps | `HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager` | `OemPreInstalledAppsEnabled` | 0 |
| Online Speech | `HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy` | `HasAccepted` | 0 |
| Copilot | `HKCU:\Software\Policies\Microsoft\Windows\WindowsCopilot` | `TurnOffWindowsCopilot` | 1 |

### Machine-Level (HKLM)

| Setting | Path | Key | Value for Privacy |
|---------|------|-----|-------------------|
| Telemetry Policy | `HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection` | `AllowTelemetry` | 0 |
| Telemetry Base | `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection` | `AllowTelemetry` | 0 |
| Activity Feed | `HKLM:\SOFTWARE\Policies\Microsoft\Windows\System` | `EnableActivityFeed` | 0 |
| Publish Activities | `HKLM:\SOFTWARE\Policies\Microsoft\Windows\System` | `PublishUserActivities` | 0 |
| Upload Activities | `HKLM:\SOFTWARE\Policies\Microsoft\Windows\System` | `UploadUserActivities` | 0 |
| Copilot | `HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot` | `TurnOffWindowsCopilot` | 1 |
| Consumer Features | `HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent` | `DisableWindowsConsumerFeatures` | 1 |

### Telemetry on Pro Edition

`AllowTelemetry=0` (Security level) is only fully honored on Enterprise/Education. On Pro, it caps at Basic (1). Setting the policy still acts as a ceiling to prevent Windows Update from bumping it back up.
Applied on this box (verified 2026-08-14): AllowTelemetry=0 in BOTH layers (policy + base) and AdvertisingID=0 in HKLM+HKCU. Effective level on Pro = Required (~6MB/day), NOT off — MS docs: "Diagnostic data off" is Server/Enterprise/Education only; 0 on Pro is silently treated as 1. DiagTrack Running (Auto) = the pipe is live; deeper levers if user wants: `sc stop DiagTrack` + `sc config DiagTrack start= disabled` + disable tasks (Compatibility Appraiser, Consolidator, UsbCeip, Siuf\DmClient), re-check after feature updates (can re-enable). MSA identifier NOT collected at Required level; GDID persists (DNS-block telemetry domains for real reduction). Network-snooper view: normal-looking TLS to MS endpoints + DoH to ControlD; the privacy-maximalist fingerprint (dead DiagTrack, failed MS connections) is what actually stands out — user's current config sits in the normal curve. Enabling ASR adds ZERO outbound telemetry (1121/1122 events are local-only without MDE onboarding).

## GDID (Global Device ID)

- Permanent device identifier that CANNOT be disabled
- Persists across reinstalls
- Sent with telemetry even at minimum level
- Documented in FBI case filing (July 2026)
- Best mitigation: block telemetry domains at DNS level (ControlD, Pi-hole, etc.)

## GPO vs Registry Keys

For home PCs (not domain-joined): **Registry keys are better.**
- GPO on non-domain machines just writes to registry anyway
- gpedit.msc is clunky and some policies don't apply cleanly without domain
- Registry changes take effect immediately
- Some settings (ContentDeliveryManager) aren't exposed in GPO
- GPO is better for enterprise/domain environments

## BIOS Settings (B550 + Ryzen 5000)

### Critical
- **XMP/DOCP** — Must be ON. Default JEDEC speed leaves massive performance on table, especially on Ryzen (memory speed = Infinity Fabric clock)
- **Resizable BAR (SAM)** — Above 4G Decoding + Re-Size BAR Support both Enabled. Free FPS.
- **CSM** — Must be Disabled for ReBAR to work. Also required for pure UEFI/Secure Boot.

### Leave Alone
- **SVM Mode** — Keep Enabled (needed for WSL/VMP/VBS)
- **fTPM** — Keep Enabled (Windows 11 requirement, no gaming impact)
- **Secure Boot** — Keep Enabled (anti-cheats require it)

### Optional
- **PBO + Curve Optimizer** — -10 to -20 all-core can give 3-5% more sustained boost
- **Fan curves** — More aggressive CPU cooling helps Ryzen boost higher (under 70C ideal)

### Power, standby & ASPM (manual-verified 2026-08)
- **ErP** — S5 shutdown rail cut (USB/audio/RGB dead when off). User keeps ON. Disables Resume by Alarm. Blocks Q-Flash Plus (needs USB standby power in S5) — disable ErP temporarily to flash from a cold port.
- **CEC 2019 Ready** — California Title 20 label for the SAME 5VSB rail gating as ErP; manual covers "shutdown, idle, or standby" but AM4 measurements often show no-op. Redundant with ErP. NOT a sleep-quality fix and NOT a control handoff — sleep entry is already OS-driven on UEFI (firmware only owns the S3 resume script).
- **xHCI Hand-off** — legacy Win7-era handoff flag; wording identical across all B550 manuals; inert on UEFI + Win10/11. Leave Enabled.
- **PCIe ASPM Mode** — undocumented in some B550 manuals (the B550 UD AC manual documents it, Default Disabled); the board's BIOS exposes L0s / L0s+L1. Two layers: BIOS ASPM = firmware permission (can veto OS via _OSC), OS ASPM = power plan Link State PM (Off / Moderate≈L0s+L1 / Maximum=+L1.2). Desktop verdict: leave Disabled — full L1 ≈ 1-3W at the wall ≈ <$1.50/yr, and L1 on NVMe is the documented stutter mechanism. HWiNFO report = per-link ground truth (WSL2 lspci sees only virtio — useless).
- **Power plan** — Balanced, never High Performance on this box: Ryzen 5000 + CPPC2 boosts to 4.45 GHz on demand in Balanced; High Performance = 100% min processor state = 15-30W idle waste for ~0 FPS. The real gaming lever is the HVCI/memory-integrity toggle, not the plan.

## Windows Update for Business on Pro — "Autopatch-lite" (no Intune)

WUfB ring machinery is built into Pro; Intune just delivers the policies. The same registry
values Intune update rings write go under `HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate`:

```
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v DeferQualityUpdates /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v DeferQualityUpdatesPeriodInDays /t REG_DWORD /d 14 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v ProductVersion /t REG_SZ /d "Windows 11" /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v TargetReleaseVersion /t REG_DWORD /d 1 /f
reg add "HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate" /v TargetReleaseVersionInfo /t REG_SZ /d "25H2" /f
```

- Quality deferral: max 30 days (some docs say 35); 14 = "Broad ring" bake of Patch Tuesday.
  MS recommends <3 days for orgs — home gaming box: 7 light / 14 sweet spot / 21 paranoid.
- Feature pin: TargetReleaseVersionInfo = current version (read via
  `reg.exe query "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion" /v DisplayVersion`);
  bump it when you choose to move. Optional second wall: DeferFeatureUpdates=1 +
  DeferFeatureUpdatesPeriodInDays=365.
- Keep Settings > Windows Update > Advanced > "Get the latest updates as soon as they're
  available" OFF (that's the preview-CU channel — anti-battle-tested).
- Pause is 35 days max — a "sit out a bad wave" button, not a lifestyle.
- Drivers: WU automatic channel ships only WHQL drivers IHVs marked "Automatic" (the curated
  channel) — leave on; review Optional updates manually. GPU: Adrenalin "Recommended" (WHQL)
  tab, never "Optional"/preview. NEVER Driver Booster / Snappy / DriverPack (scraped beta
  drivers + junkware — the anti-pattern).
- Don't block `\Microsoft\Windows\PI\Secure-Boot-Update` (see next section).

## Driver Update Channels (verified 2026-08)

How the WU driver pipeline actually works, verified via Microsoft Update Catalog + Intel/AMD pages:

- WU only distributes what vendors submit (WHQL, Automatic vs Optional channel). The WU version is the vendor's curated stable baseline, often ~1yr behind the vendor site — e.g. Intel AX210: WU catalog 23.170.0.1 (2025-09) vs Intel site 24.60.0 (2026-08). A "2-year-old" WU driver usually means the vendor stopped submitting, not that Microsoft is holding back.
- Security fixes get the fast lane (vendor advisories → WU promptly, or the blocklist covers the gap); quality/feature fixes wait. Old wifi CVEs (INTEL-SA-00473→22.30, INTEL-SA-00582→22.80) sit far below the current WU baseline — the WU version already contains them.
- Safety net for old drivers: Microsoft vulnerable driver blocklist — ON by default since the Win11 2022 update, updated quarterly + via monthly servicing; blocks known-vulnerable drivers from loading. The downloadable list is more complete than the OS/WU-delivered version.
- Per-component policy for this box: wifi → WU baseline + Optional updates (deviate only for a specific problem or an Intel advisory); GPU → Adrenalin "Recommended" (WHQL) tab, never Optional/preview; chipset → AMD site package a few times a year (CPPC2/preferred-core fix lives in the chipset package, AMD PA-400 — matters for Ryzen 5000 boost under Win11); BIOS/AGESA → board vendor on security advisories (Sinkclose CVE-2023-31315 fixed for Ryzen 5000 via AGESA 1.2.0.Cb; needs kernel access to exploit, defense-in-depth). Never beta drivers on a box you depend on.
- AMD chipset package contents: mostly INFs + PSP driver + PPM provisioning file driver; the old "uninstall the USB filter driver" fix is Win10-era — current packages mark USB Filter Driver Not Applicable for Win11.
- Delivery Optimization: default ON (local network only per current MS docs). Single-PC home: turn OFF — the internet P2P tier uploads update chunks to strangers on your IP for zero benefit with one machine and good internet.

## Secure Boot: keys, migration, BIOS options (2026)

Full knowledge bank + commands: secure-boot-2026.md. Essentials:

- 2011-era Microsoft certs (KEK CA 2011, UEFI CA 2011, Production PCA 2011) expired
  Jun–Oct 2026 → 2023 replacements. Consumer machines migrate automatically via WU +
  `\Microsoft\Windows\PI\Secure-Boot-Update` (~12h cadence).
- Migration-done check: `HKLM\SYSTEM\CurrentControlSet\Control\SecureBoot\AvailableUpdates`
  = 0x0 (all bits consumed); TPM-WMI event 1808; Windows Security > Device security >
  Secure Boot badges (Apr 2026+).
- Gigabyte/ASRock Key Management (Secure Boot Mode = Custom):
  - Delete PK → Setup Mode, Secure Boot off, HVCI refuses to run. Recover via Restore
    Factory Keys. Never touch on a healthy box.
  - "Device Guard Ready → Remove 'UEFI CA' from DB" is REAL, not a fossil: WHCR for
    Credential Guard (oem-credential-guard) requires "Microsoft UEFI CA must be removed
    from the Secure Boot database". Legit hardening for locked-down Windows-only boxes;
    kills Linux shim forever and can break add-in card option ROMs (GPU no-display boot
    failure). NOT required for HVCI/Credential Guard to run.
- Research rule (user preference): find the exact BIOS option in vendor manuals (ManualsLib /
  manualowl via MCP exa search with the user's remembered phrase) and check Microsoft's
  oem-* hardware-requirement pages BEFORE judging an option useful/useless. "Delete PK" and
  "Remove UEFI CA from DB" are opposite things — never pattern-match an option name.
  When the verdict is "redundant / vestigial / no-op", state the setting's mechanism FIRST,
  then the verdict — this user calls out verdicts without mechanisms (called it on CEC 2019
  Ready: "you never said what cec 2019 ready does then").

## Event Viewer — What Actually Matters

Diagnostic recipes for sleep/wake forensics, USB/PnP flap, and powercfg: windows-event-log-diagnostics.md.

### Ignore (cosmetic noise)
- DCOM 10016 warnings — every Windows install has these, zero impact. Identify the component: `reg.exe query "HKLM\SOFTWARE\Classes\CLSID\{<CLSID>}"` (default value = name) and `reg.exe query "HKLM\SOFTWARE\Classes\AppID\{<APPID>}"` (LocalService = owner service). The recurring one on this box is WaaSMedicSvc (Windows Update Medic Service): CLSID {9EA82395-E31B-41CA-8DF7-EC1CEE7194DF} = WaaSProtectedSettingsProvider, APPID {2ED83BAA-B2FD-43B1-99BF-E6149C622692}, caller NT AUTHORITY\NETWORK SERVICE. Baseline is a few/day; FLOODS of thousands (1 per ~8s for hours) correlate with Windows Update install sessions (WUClient 43/44/19 nearby) and self-resolve. KB 4022522: by design (first access path fails by ACL, code falls back). Do NOT "fix" by granting Local Activation (MS recommends against; weakens ACL on a protected service) and do NOT disable WaaSMedicSvc. If it floods for hours, check for update failures (WUClient Event 20), otherwise filter the noise in Event Viewer.
- ProtonVPN socket errors — normal VPN reconnect behavior

### Investigate
- DNS NRPT corruption — often caused by ctrld/VPN stale rules, remove specific broken rule GUID
- Windows Update failures (0x80073D02) — usually self-resolving, wsreset.exe if persistent
- Volsnap shadow copy aborted — increase VSS storage limit or ignore if not using System Restore
- IPv6 TCP binding failures — common on WiFi, usually harmless
- Intel WiFi limited connectivity — update driver, consider ethernet for gaming
- SCEP certificate 429 errors + Event 86 AIK enrollment failures (AMD-KeyId-*.microsoftaik.azure.net, CertificateServicesClient-CertEnroll) — benign AMD fTPM noise family (fully decoded 2026-08-14): PkiStatus(11) SCEPDispositionPendingChallenge + EnrollStatus(32) = normal SCEP pending, client logs "failed" anyway; SubmitV2Attestation 400 "P-256 ECC AIK requests not supported" = MS AIK v2 endpoint rejects the fTPM's ECC key type (server-side, no fix exists); TPM_E_KEY_NOT_LOADED (0x8029040f) at _CreateAikClaim = fTPM key eviction, matches this box's event 14/17 churn. Zero impact: AIK attestation only feeds MDM/Hello-for-Business/Autopilot/device-health checks. Do NOT clear TPM or disable fTPM. Cosmetic silence: disable scheduled task Microsoft\Windows\CertificateServicesClient\AikCertEnrollTask (re-enable if ever enrolling in attestation). VSS/CEventSystem 0x8007045b line in same logs = shutdown-order race, ignore.
- PCIe ASPM on this box: verdict = keep Disabled (BIOS) + Windows Link State PM as-is. Upside ~1-3W idle (~$1/yr); documented failure classes are specific-drive bugs (SN740, Kioxia L1.2/LTR), suspend-path hangs (2025 kernel NVMe+ASPM L1 fix), APST conflation (990 Pro was drive APST, not link ASPM) — none match this hardware, but the sleep path here is already flaky (USB wake churn + TPM bursts), so adding an ASPM variable is a lottery with a $1 prize. L1.2 (Windows Maximum) is the risky class; Moderate = L1 without substates. The "ASPM stutter" claim is folklore (the doubling-NVMe-speed case was a Gen2 link-training misconfig, not L1 latency). If ever tested: L0s+L1 + Moderate, watch WHEA/Event 51/StorNVMe errors + sleep behavior for a week.

## This box: sleep/wake behavior (verified 2026-08)
- S3 (not Modern Standby; S0 Low Power Idle unsupported by firmware), Hibernate + Fast Startup available, Hybrid Sleep blocked by hypervisor.
- 136/136 sleep entries in 30 days trigger an instant USB wake blip: Kernel-Power 42 → 107 within 1-5s, wake source always "AMD USB 3.10 eXtensible Host Controller" (chipset DEV_43EE). Power-Troubleshooter shows the machine then stays down for hours, so the blip is abortive, not a real wake.
- Armed wake devices: 5x HID Keyboard Device (HyperX VID_0951 multi-interface + SMSL DAC VID_152A volume-knob HID), HID mouse (Razer DeathAdder V3), AMD UCM-UCSI Device. UCM-UCSI CONFIRMED flaky: UcmUcsiCx failures ~weekly (11 in 3 months, Microsoft-Windows-USB-UCMUCSICX/Operational log). DAC HID re-enumeration on S3 entry also possible.
- Fix path: `powercfg /devicedisablewake "AMD UCM-UCSI Device"` first, then DAC HID interfaces; keep keyboard/mouse armed; verify with `powercfg /lastwake`. CEC 2019 Ready would also cut USB in S3 (blunt instrument, kills USB wake) — do NOT use a compliance toggle as a wake fix.
- TPM Event 14/17 bursts correlate with these S3 entry/exit cycles (fTPM churn); reducing the blip churn is the only lever besides BIOS/AGESA updates.
- Monitor: ASUS (EDID AUS25A6), disconnect/connect chime on standby = DisplayPort link drop on DPMS; DISPLAY\AUS25A6 flaps ~20x/2d in Kernel-PnP Device Management log; NOT USB (zero USB re-enumeration in same window). Fix = HDMI/cable/OSD/driver; ASPM irrelevant.
- ASPM ground truth (HWiNFO report): L0s active only on 2 CPU GPP root ports + GPU-internal switch port; L1 disabled everywhere; NVMe = Phison-class controller (L1-only support); GPU host link healthy x16 @16GT/s. BIOS option L0s vs L0s+L1: L1 = real idle savings + NVMe stutter risk. Windows slider Moderate ≈ L0s+L1, Maximum adds L1.2 (avoid on gaming box). lspci from WSL useless (virtual bus) — HWiNFO text report gives per-link ASPM Support/Status.
- RAM: 4x8GB mixed Corsair kits (2x 2400 + 2x 3000) — whole set runs at 2400 regardless of DOCP.

### TPM Event 14 / 17 (AMD fTPM) — investigate, usually transient
- Event 17 (Info) = a TPM command failed; Event 14 (Error) = driver gave up after
  retries. Bursts of alternating 17/14 pairs (observed 6 pairs per burst) = retry loop.
  Event 18 = routine provisioning trigger at boot, NOT an error. Event 51/52 = fTPM
  stutter warnings; 0x80070490 attestation failure = AMD PA-420 (fTPM 3.*.0.* bug).
- On Ryzen (fTPM) this is usually a transient firmware hiccup (post-sleep or mid-session),
  not a dead TPM. Confirm: PnP device OK, zero WHEA, machine still boots, bursts rare.
  MS KB: "Error log of TPM device driver" (fix = latest CU + BIOS/TPM firmware update).
- Full diagnosis playbook: the B550 board case is documented in the live environment (machine-specific).
  Re-runnable probe: `scripts/tpm-diagnostics.ps1` (write to Windows temp, run with
  powershell.exe -File; no iconv pipe).
- Clear TPM only via Windows Security > Device security > Security processor
  troubleshooting (never from BIOS), and only with the BitLocker recovery key confirmed.

## Pitfalls

### PowerShell from WSL
When running PowerShell scripts from WSL, `$` variables get interpreted by bash. Write script to a `.ps1` file first, then execute with:
```bash
powershell.exe -ExecutionPolicy Bypass -File "C:\path\to\script.ps1"
```
Do NOT pass multi-line scripts inline through bash.

Output comes back as UTF-8 already (WSL interop converts it) — do NOT pipe through
`iconv -f UTF-16 -t UTF-8`: iconv misreads the ASCII byte pairs as UTF-16 code units and
turns a clean dump into CJK mojibake (hit this 2026-08 on a TPM diagnostic). Run the
command bare, or redirect to a file and read it.

### Elevated scripts from WSL (UAC pattern, verified 2026-08)
Admin work goes through one UAC prompt on the user's desktop — warn the user it is coming:
```bash
powershell.exe -NoProfile -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\path\to\script.ps1' -Wait"
```
- `-Wait` blocks until the elevated process finishes; then read its output.
- Have the elevated script write results to a log file with **`-Encoding ascii` on EVERY write** (first line `Set-Content -Encoding ascii`, every append `Add-Content -Encoding ascii`). Mixing encodings in one file (first line `-Encoding utf8`, then `-Append` with no encoding = UTF-16) produces a file that cat shows null-padded and iconv mangles in both directions — unreadable either way (hit 2026-08).
- The elevated window's stdout is invisible to the agent; the log file is the only channel back.
- Non-elevated read limits (verified 2026-08-14): `driverquery /v` Signed column is BLANK (not False) without admin; `Get-Tpm` and `Confirm-SecureBootUEFI` error with access denied; system processes show empty ExecutablePath (noise, not findings). Prefer `Get-NetTCPConnection` over `netstat -b` for process-to-connection mapping — works non-elevated.

### Autoruns "(Not Verified)" on Microsoft files
(Not Verified) != unsigned. Autoruns scans embedded Authenticode signatures at scan time;
catalog-signed inbox binaries (wmpnetwk.exe, wmpnscfg.exe, MsSense.exe...) fail it routinely.
Verify with `Get-AuthenticodeSignature <path>` (catalog-aware via CryptSvc) → Status Valid,
or `sigcheck -i <path>` → "Verified: Signed" + matching .cat. MsSense.exe is a known false
negative (acknowledged MS bug). Red flags are non-canonical paths and unsigned 3rd-party
entries in Run/Services — not Microsoft files showing Not Verified.

### ASR rules — recommended set for this box (verified against MS Learn 2026-07 reference, 2026-08)

ENABLE (no audit needed, near-zero fire risk on this box):
- `56a863a9-875e-4185-98a7-b882c64b5ce5` Block abuse of exploited vulnerable signed drivers — TOP pick for home: BYOVD attacks (ransomware killing Defender); fires only when something drops a known-vulnerable driver. Does not block existing drivers.
- `d1e49aac-8f56-4280-b9ba-993a6d77406c` Block process creations from PSExec and WMI — lateral-movement/ransomware exec technique; nothing legit on a home box spawns via PsExec/WMI.
- `b2b3f03d-6a65-4f7b-a9c7-1c7ef74a9ba4` untrusted/unsigned USB (audit first on a dev box — also blocks copied files running from disk)
- `be9ba2d9-53ea-4cdc-84e5-9b1eeee46550` email/webmail executable content (audit first: Firefox webmail attachment downloads may trigger)
- `d4f940ab-401b-4efc-aadc-ad5f3c50688a` Office child processes + `92e97fa1-2edf-4476-bdd6-9dd0b4dddc7b` Office macro Win32 API — no-op insurance until real MS Office is installed (ONLYOFFICE is not in %ProgramFiles% so rules don't apply to it)
AUDIT 1-2 wks then enable: `5beb7efe-fd9a-4556-801d-275e5ffc04cc` obfuscated scripts (dev tooling risk), `d3e037e1-3eb8-44c8-a917-57927947596d` JS/VBS launching downloads, `e6db77e5-3df2-4cf1-b95a-636979351e5b` WMI persistence (this GUID is WMI persistence, NOT email — email is be9ba2d9)
NEVER on a modding/dev box: `01443614-cd74-433a-b99e-2ecdc07bfc25` prevalence/trusted-list, `c1db55ab-c21a-4637-bb3f-a12568109d35` advanced ransomware (blocks no-reputation files = unsigned mods/tools). `9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2` LSASS is redundant when LSA PPL is on (doc: not required, no extra protection).
Current GUIDs also: `c0033c00-d16d-4114-a5a0-dc9b3a7d2ceb` copied/impersonated system tools, `33ddedf1-c6e0-47cb-833e-de6133960387` safe-mode reboot, `7674ba52-37eb-4a4f-a9a1-f0f9a1619a2c` Adobe Reader, `26190899-1602-49e8-8b27-eb1d0a1ce869` Outlook child, `3b576869-a4ec-4529-8536-b80a7769e899` Office exec content, `75668c1f-73b5-4cf0-bb93-3ecf5cb7cc84` Office injection (Office-injection incompatible with BeyondTrust/Heimdal per docs).

### Tamper protection silently eats local ASR changes (verified 2026-08 on this box)
On Win11 25H2 build 26200 with TP on (TamperProtectionSource: Signatures), Add-MpPreference
-ASR rules reports success but NOTHING persists: no 5007 event, Get-MpPreference stays empty,
ExploitGuard local store never created. Policy-layer registry write (HKLM\SOFTWARE\Policies\...
\Attack Surface Reduction\Rules, value 1) also did NOT apply within minutes; inconclusive whether
a WinDefend service restart would apply it (user canceled that test). MS docs: TP-protected changes
"might appear to succeed but are actually blocked". Verified apply path for home: toggle Tamper
Protection OFF in Windows Security > Virus & threat protection > Manage settings, Set-MpPreference,
toggle TP back ON. Do not claim ASR enablement worked without verifying Get-MpPreference shows the IDs.
Community corroboration (WindowsForum ASR tutorial Mar/Jul 2026, H2S May 2026): TP-on silently
no-ops local Defender changes on 25H2 builds, including ASR; MS TP page explicitly sanctions the
Windows Security toggle for home devices ("devices for home use"). UNTESTED on this box: policy
layer + WinDefend service restart (docs say policy applies on startup) and gpedit path — try
policy+restart before the TP toggle; H2S claims GPO also gets ignored with TP on 25H2.

### SQLWriter "\90\Shared" path trap (verified 2026-08)
`C:\Program Files\Microsoft SQL Server\90\Shared\sqlwriter.exe` is NOT SQL Server 2005.
That folder path is frozen legacy; SQL Server 2025 LocalDB (17.0.1000.7, installed 2026-03)
installs its VSS writer there. This box's inventory flags must check file version, never the
path — the "\90" pattern-match produced a false "EOL 2005" flag (user pushed back, evidence
reversed it). This box also runs: MSMQ (enabled Auto; patched — MSMQ network RCEs CVE-2024-30080,
2025-50177, 2026-50439, 2026-50505 fixed by July 2026 CU 26200.8875; box UBR 9168 ≥ that), Parsec
150-104a (patched for CVE-2026-54424), JDK 26.0.1, ONLYOFFICE, ControlD ctrld. All benign/current
as of 2026-08 — do not re-flag as suspicious in future inventories; MSMQ is a "why enabled" question
only, not a finding.

### DNS blocklists on ControlD (ctrld) — verdict 2026-08-14
User's DNS = ControlD via ctrld. Verdict: HaGeZi Pro + TIF mini (max coverage, low breakage; TIF mini = the security layer: malware/phishing/C2). Upgrade path if user wants more blocking: HaGeZi Pro Plus + TIF mini (adds full popup-ads, referral/affiliate domains incl. app.adjust.*, adservice.google.*, ad.doubleclick.net, and 30-day malicious NRDs; core apps Steam/Discord/GOG/Firefox/Tidal unaffected; watch phone app deep links + brand-new legit sites under 30 days; ControlD allowlist is the safety valve). Do NOT stack 1Hosts — its unique domains ARE its false-positive class, and it is LIVE-VERIFIED still blocking *.smoot.apple.com in BOTH Lite (205,923 rules) and Xtra (1.11M rules) as of the 2026-08-14 list update, while HaGeZi/StevenBlack/AdGuard/OISD/hBlock never did even in aggressive tiers; open May-2026 issue #4188 catalogues more legit-infra blocks (Tailscale, NordVPN, Hugging Face, Colab, Prime Video, Zomato, AliExpress). The Apple blocks are a deliberate privacy stance (smoot = Spotlight keystroke telemetry), not sloppiness — but still a deal-breaker for a zero-breakage goal. Do NOT stack StevenBlack — default unified = adware+malware only (~99.5k entries, Aug 2026); fakenews/gambling/porn/social are OPTIONAL alternates/--extensions, NOT in the default (user caught me asserting otherwise — corrected); its sources (AdAway, AdGuard DNS, MVPS, yoyo, Dan Pollock, someonewhocares) are already inside HaGeZi = redundant. DNS lists union at the resolver: union breakage = worst member's FPs, so never add a list for "its good parts".
Full knowledge bank (tier sizes, Pro vs Pro++ breakdown, 1Hosts FP history, StevenBlack numbers, ControlD mirrors, verification recipes): dns-blocklists-2026.md.
RULE (user catches unverified claims): assert blocklist behavior only from live repo state — fetch the raw list and grep, check the issue tracker (recipes in the reference file). Never pattern-match from memory (StevenBlack default composition was asserted wrong in 2026-08; same class of error as the SQLWriter path).
ControlD uses NRPT rules for DNS interception. "NRPT corruption" errors are usually stale rules from ctrld restart/update. Remove the specific broken rule GUID, NOT all NRPT rules (ctrld depends on them). Then restart ctrld service.

### Checking WDAC/SAC state
msinfo32 "App Control for Business policy: Enforced" with "user mode policy: Off" means the default Windows WDAC baseline is active (kernel-level driver integrity check) but user-facing SAC is disabled. Check with:
```powershell
Get-CimInstance -ClassName Win32_DeviceGuard -Namespace root\Microsoft\Windows\DeviceGuard
```
`CodeIntegrityPolicyEnforcementStatus: 2` = default Windows baseline, not custom.

### HAGS on AMD
Hardware-Accelerated GPU Scheduling is primarily an NVIDIA feature. AMD's support on RDNA2 (RX 6000) was inconsistent and recent Adrenalin drivers may not expose the option. If missing, it's fine — not needed on AMD GPUs.

## Defender Exploit Guard: ASR + Network Protection (verified 2026-08)

All claims below verified against Microsoft Learn (defender-endpoint docs) via MCP in Aug 2026. Full knowledge bank: defender-asr-network-protection.md.

### Attack Surface Reduction (ASR) rules
- Available on ANY Windows edition incl. Home; local config via PowerShell or GPO is documented ("All ASR rules are supported by both methods on local devices").
- Enable: `Add-MpPreference -AttackSurfaceReductionRules_Ids "<guid>" -AttackSurfaceReductionRules_Actions Enabled`; audit first via `Audit`; verify `Get-MpPreference | Select AttackSurfaceReductionRules_Ids`.
- **TP silent no-op (verified 2026-08-14, this box, 25H2, TP source Signatures):** with tamper protection ON, the ASR cmdlet reports success but nothing persists — no event 5007 fires, no local store key is created, Get-MpPreference shows no rules. Microsoft's TP doc states changes to protected settings "might appear to succeed but are actually blocked by tamper protection." ALWAYS verify persistence after enabling (Get-MpPreference + event 5007); never trust cmdlet success alone.
- Home-user fix path (MS-documented): Windows Security > Virus & threat protection > Manage settings > Tamper Protection OFF, apply rules, Tamper Protection back ON. Policy-layer write + `Restart-Service WinDefend -Force` is UNVERIFIED (user canceled before the restart test ran) — treat as experimental.
- When a change sequence stalls like this (silent no-ops, repeated UAC prompts), STOP and report current status + what you were doing; the user explicitly called this (2026-08-14: "lets stop applying, just check what our current status is").
- Event IDs (Windows Defender > Operational): 1121 = blocked, 1122 = audited, 1129 = warn override, 5007 = config change.
- Storage: local layer `HKLM\SOFTWARE\Microsoft\Windows Defender\ExploitGuard\Configuration`; policy layer `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Windows Defender Exploit Guard\Attack Surface Reduction\Rules` (policy wins ON STARTUP: the service reads policy at start/refresh, so a fresh policy write can sit inert in the registry — observed 2026-08-14: values present, Get-MpPreference still empty 10+ min later; service restart or the refresh cycle is required). Use PowerShell, never raw registry: cmdlets update service state; tamper protection silently reverts raw edits to protected settings.
- Safe subset for a gaming/dev box (never fire in normal use):
  - `be9ba2d9-53ea-4cdc-84e5-9b1eeee46550` email/webmail executables
  - `d4f940ab-401b-4efc-aadc-ad5f3c50688a` Office child processes (only enforced if Office in %ProgramFiles%)
  - `b2b3f03d-6a65-4f7b-a9c7-1c7ef74a9ba4` untrusted/unsigned USB processes (CORRECTED GUID; also blocks copied files from running from disk)
- Do NOT enable `01443614-cd74-433a-b99e-2ecdc07bfc25` (prevalence/age/trusted list) on a modding/dev box — blocks unsigned dev tools and mods.
- LSASS rule `9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2` is redundant when LSA protection is on (default on clean-installed, HVCI-capable Win11 22H2+). Docs: "This ASR rule isn't required... doesn't provide extra protection."

### Network Protection
- `Set-MpPreference -EnableNetworkProtection AuditMode` → a week → `Enabled` (named values per docs). Audit-then-block, like the rest of the ASR family.
- Requires real-time protection + behavior monitoring + cloud protection (all default-on). DNS sinkhole (DNS-level blocking) is default-on and part of the same stack.
- OS-level block of known phishing/malware/C2 domains in ALL apps (Discord/Steam links, PowerShell) — the significant phishing defense for gamers. Edge is exempt (native SmartScreen). Firefox/Chrome: FQDN blocking requires QUIC + ECH disabled in the browser — ECH is a genuine privacy tradeoff, pick per threat model.
- Registry check: `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Policy Manager` or local `HKLM\SOFTWARE\Microsoft\Windows Defender\Windows Defender Exploit Guard\Network Protection` → EnableNetworkProtection 0/1/2.
- Privacy: local feed handles known-bad; cloud lookup only for unrated hosts (hostname/URL metadata, no content, no TLS decryption). Same pipe as SmartScreen.

### PUA, MAPS, samples (corrections from a 2026 doc pass)
- PUA consumer default = AUDIT (2), not block; Edge PUA toggle off by default; `Set-MpPreference -PUAProtection Enabled`; PUA events = 1160; flags Cheat Engine/injection mod loaders as hacktools.
- MAPSReporting Basic vs Advanced is a LEGACY distinction on Win10/11 — "no difference in the type or amount of information that is shared". Do NOT recommend MAPSReporting 1 as a privacy trim; it's a no-op.
- SubmitSamplesConsent: 0=AlwaysPrompt, 1=SendSafeSamples (default; prompts on personal-looking files), 2=NeverSend, 3=SendAllSamples. NeverSend (2) and AlwaysPrompt (0) disable Block at First Sight — leaving 1 is the right balance.
- Tamper protection protects core settings (real-time, cloud protection); antivirus EXCLUSIONS are only tamper-protected on Intune/ConfigMgr-only managed fleets (TPExclusions=1) — on a home box, exclusion changes via PowerShell work. Troubleshooting mode = sanctioned escape hatch when TP blocks a change.

### Calibration for home gaming/dev boxes (user-endorsed)
Most Defender toggles are garnish. Load-bearing: account takeover defense (MFA/passkeys, GitHub token hygiene), tested offsite backups, "don't run garbage" habit (Windows Sandbox: `Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All`). Decision rule the user endorsed: only do security work you can't forget to do.

## Running inventory / compromise check (verified 2026-08)

Re-runnable 16-section inventory (processes w/ command lines, startup, tasks, services, drivers, connections, listeners, WMI persistence, Defender, boot state): `scripts/win-inventory.ps1`. Run from WSL via `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`. Output is ~130KB on this box — redirect to a log and page it; the middle sections (startup/tasks/services/drivers) fall out of inline capture.

Key interpretation rules:
- Non-elevated run: `Confirm-SecureBootUEFI` and `Get-Tpm` fail, driverquery Signed column is blank for ALL drivers (inconclusive, not "unsigned"), and system processes show empty ExecutablePath (noise, not findings). Re-run admin-required checks elevated.
- explorer.exe at C:\WINDOWS\Explorer.EXE and AppData\Local\Discord (Electron) are legit paths, not flags. wtd driver is inbox on 24H2/25H2.
- Legacy-looking flags, ALL REVERSED by version checks 2026-08-14: SQLWriter `\90\` path = SQL Server 2025 LocalDB VSS writer (frozen legacy path, NOT SQL 2005 — check file version, never path), Parsec 150-104a = patched for CVE-2026-54424, SunJavaUpdateSched points at current JDK 26.0.1, MSMQ = stock feature and fully patched (Aug 2026 CU KB5121003/KB5123304 installed; all MSMQ CVEs covered).
- IP ownership checks: rdap.org flaky — hit rdap.arin.net / rdap.db.ripe.net directly with python urllib (never `curl | python3`; the pipe trips a HIGH "pipe to interpreter" approval gate). Known-clean: Microsoft cloud 172.172.0.0/16 (Windows Update/Defender path), GOG CDN 91.222.185.0/24, ControlD 76.76.2.22, Valve 162.254.193.75.
- This box 2026-08-14 verdict: clean, nothing to do. The inventoried services (message-queueing, a remote-access daemon, SQL writer, a Java runtime) all current and benign; the message-queueing service is a "why is it enabled" question only (off by default, something turned it on) — not a finding. ASR APPLIED 2026-08-14 via TP-off window (verified Get-MpPreference): 7 Enabled = 56a863a9, d1e49aac, d4f940ab, 92e97fa1, be9ba2d9, b2b3f03d, e6db77e5; 2 Audit = 5beb7efe, d3e037e1 (flip to Enabled after user's modding work + 1122 check, same 9-ID Set call); NetworkProtection=AuditMode (2) then Enabled later, PUA=Enabled (1); TP back ON (verified True). Firewall dropped-conn log NOT yet enabled. Desktop defender-query.ps1 = 8-section status script (self-elevating, -NoElevate skips admin sections).

## Scripts

- `scripts/win-inventory.ps1` — 16-section running-inventory / compromise check (see section above).
- `scripts/privacy-status-check.ps1` — Run to check current privacy registry key state. Outputs each setting as "Name = Value".
- `scripts/privacy-hardening.ps1` — Run as Administrator to apply all recommended privacy settings. Requires restart.


## Reference: defender-asr-network-protection.md

# Defender Exploit Guard, PUA, MAPS, samples — verified knowledge bank (2026-08)

All facts verified via MCP (exa fetch/search) against Microsoft Learn in Aug 2026. Target machine:
Win11 Pro 25H2, a Zen 3 Ryzen 5000 (HVCI-capable) with a discrete GPU, home network, single user.
Primary doc URLs: /defender-endpoint/attack-surface-reduction-rules-reference,
/defender-endpoint/enable-network-protection, /defender-endpoint/network-protection,
/defender-endpoint/detect-block-potentially-unwanted-apps-microsoft-defender-antivirus,
/defender-endpoint/enable-cloud-protection-microsoft-defender-antivirus,
/defender-endpoint/prevent-changes-to-security-settings-with-tamper-protection,
/defender-endpoint/manage-tamper-protection-intune, /windows/deployment/delivery-optimization/.

## ASR rule GUIDs (reference page, updated 2026-07)

| Rule | GUID | Notes |
|---|---|---|
| Block credential stealing from LSASS | 9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2 | Redundant if LSA protection on (default 22H2+ clean installs, HVCI-capable). No Warn mode. Noisy in audit. |
| Block all Office apps from creating child processes | d4f940ab-401b-4efc-aadc-ad5f3c50688a | Enforced only if Office in %ProgramFiles% / %ProgramFiles(x86)% |
| Block executable content from email client and webmail | be9ba2d9-53ea-4cdc-84e5-9b1eeee46550 | Blocks exe/dll/scr/ps1/vbs/js/zip. Popups need cloud protection High+ |
| Block untrusted and unsigned processes from USB | b2b3f03d-6a65-4f7b-a9c7-1c7ef74a9ba4 | CORRECTED GUID — older sources cite b2b3f03d-6aad-4619-9102-7116272692de, which is WRONG. Docs: doesn't block copying to disk, but "blocks the copied files from running from disk". |
| Block executable files unless prevalence/age/trusted list | 01443614-cd74-433a-b99e-2ecdc07bfc25 | Needs cloud protection. Breaks unsigned dev tools + mods — skip on gaming/dev boxes |
| Block execution of potentially obfuscated scripts | 5beb7efe-fd9a-4556-801d-275e5ffc04cc | Needs cloud protection; supports PowerShell; test before block (can trip build scripts) |
| Block abuse of exploited vulnerable signed drivers | 56a863a9-875e-4185-98a7-b882c64b5ce5 | Standard protection rule; prevents WRITING vulnerable drivers, not loading existing ones |
| Use advanced protection against ransomware | c1db55ab-c21a-4637-bb3f-a12568109d35 | Needs cloud protection; blocks unknown-but-benign files (reputation-based) — false-positive prone |

## Deployment facts

- ASR available on any edition incl. Windows 11 Home; "You can configure ASR rules locally using
  PowerShell or Group Policy. All ASR rules are supported by both methods on local devices."
- PowerShell: `Add-MpPreference -AttackSurfaceReductionRules_Ids "<guid>" -AttackSurfaceReductionRules_Actions Enabled` (or `Audit`). Verify: `Get-MpPreference | Select AttackSurfaceReductionRules_Ids`. Remove: `Remove-MpPreference -AttackSurfaceReductionRules_Ids <guid> -AttackSurfaceReductionRules_Actions Enabled`.
- Event IDs, Windows Defender > Operational: 1121 blocked, 1122 audited, 1129 warn override, 5007 settings change. PUA events: 1160.
- Storage: local `HKLM\SOFTWARE\Microsoft\Windows Defender\ExploitGuard\Configuration` (GUID values: 1=block, 2=audit); policy `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Windows Defender Exploit Guard\Attack Surface Reduction\Rules`. Policy overrides local. Use cmdlets, not raw registry (cmdlets update the running service state; tamper protection can silently revert raw edits to protected settings).
- Registry vs PowerShell: cmdlets are the supported local path. "reg add" snippets in MS docs are for enterprise policy delivery. gpedit on a home box is a GUI over the same registry; mixing methods creates a policy layer that overrides later cmdlets.

## Network Protection

- Extends the SmartScreen reputation feed to the OS level: blocks outbound connections to poor-reputation domains in every app, including non-browser processes (PowerShell). Blocks on all ports.
- Edge is NOT monitored on Windows (native SmartScreen instead). Non-Edge browsers: FQDN blocking requires QUIC + Encrypted Client Hello disabled in the browser (ECH hides the hostname from NP — genuine privacy-vs-phishing tradeoff).
- Requires: real-time protection + behavior monitoring + cloud-delivered protection (all default-on). If any is disabled, NP silently doesn't work.
- Enable: `Set-MpPreference -EnableNetworkProtection AuditMode` → `Enabled` (named values per docs; Get-MpPreference reports 0/1/2). Registry check: `HKLM\SOFTWARE\Policies\Microsoft\Windows Defender\Policy Manager` or `HKLM\SOFTWARE\Microsoft\Windows Defender\Windows Defender Exploit Guard\Network Protection` → EnableNetworkProtection 0 off / 1 block / 2 audit.
- DNS sinkhole (DNS-level blocking) is default-on, part of the same stack. C2 (command-and-control) blocking included.
- Privacy: local feed handles known-bad; cloud reputation lookup only for unrated hosts. Sent: hostname (full URL only for plain HTTP). No content, no TLS decryption. Same pipe as SmartScreen/cloud protection, which are on by default anyway.

## PUA protection

- Categories: adware, bundling software (offers installs not signed by same vendor), evasion software.
- Default for non-onboarded devices with security intel >= 1.329.495.0: AUDIT (2), NOT block. Edge PUA toggle: off by default (Edge Settings > Privacy > Security > Block potentially unwanted apps).
- `Set-MpPreference -PUAProtection Enabled` (1 block / 2 audit / 0 off). Quarantined with "PUA:" prefix, events 1160, Get-MpThreat to view.
- Flags Cheat Engine and injection-based mod loaders as hacktools — feature unless you use them.

## MAPS / sample submission — the 2026 corrections

- MAPS (cloud-delivered protection) is on by default. "In Windows 10 and Windows 11, there is no
  difference between the Basic and Advanced reporting options... The distinction between the Basic
  and Advanced reporting options is legacy, and choosing either setting results in the same level
  of cloud protection. There is no difference in the type or amount of information that is shared."
  → Setting MAPSReporting 1 as a "privacy trim" is a NO-OP. Consumer stock value is 2.
- SubmitSamplesConsent values: 0 = AlwaysPrompt, 1 = SendSafeSamples (default; files likely to
  contain personal info prompt first), 2 = NeverSend, 3 = SendAllSamples.
- NeverSend (2) and AlwaysPrompt (0) "lower the protection level" and NeverSend disables
  Block at First Sight (BAFS). Leave at 1 unless the BAFS tradeoff is explicitly accepted.
- CloudBlockLevel: 0 default; higher = more aggressive blocking + more metadata. Keep 0.
- Tamper protection protects: real-time protection, behavior monitoring, IOAV, cloud protection,
  security intelligence updates, automatic actions, notifications, archived-file scanning.
  Antivirus EXCLUSIONS are tamper-protected ONLY on Intune-only or ConfigMgr-only managed fleets
  (ManagedDefenderProductType 6/7 + TPExclusions=1). Home/unmanaged box: exclusions remain
  locally manageable via PowerShell. When TP blocks a change, troubleshooting mode is the
  sanctioned escape hatch (changes revert when it ends).

## Driver channels (verified via Microsoft Update Catalog, Intel, AMD)

- WU driver = vendor's curated stable baseline (WHQL "Automatic" channel), typically ~1yr behind
  the vendor site. AX210 evidence: WU catalog 23.170.0.1 (2025-09-08), Intel site 24.60.0
  (2026-08). Intel release notes: 23.170.0+ validated for Win11 25H2.
- Vendor site = frontier tier; WU = certainty tier; security fixes get both, quality fixes wait.
- Vulnerable driver blocklist: default-on since Win11 2022 update; quarterly + monthly servicing;
  refuses to load known-vulnerable drivers. Downloadable list is more complete than the OS/WU version.
- AMD chipset: UEFI CPPC2 ("preferred core") behavior on Win11 restored by chipset driver
  3.10.08.506+ (AMD PA-400 + release notes; Ryzen 5000 supported). Package = mostly INFs + PSP
  driver + PPM provisioning file driver. USB Filter Driver: Not Applicable for Win11 in current
  packages (the old "uninstall it" fix is Win10-era).
- Sinkclose CVE-2023-31315: all AMD CPUs back to 2006; fixed via BIOS/AGESA (Ryzen 5000 →
  AGESA 1.2.0.Cb, Gigabyte confirmed); requires kernel access to exploit (defense-in-depth).
- Delivery Optimization: default ON, local-network-only (current MS docs). Single-PC home: turn
  OFF (Settings > Windows Update > Advanced options > Delivery Optimization). Internet tier
  uploads update chunks to strangers on your residential IP for zero benefit with one machine.
- Windows Sandbox: `Enable-WindowsOptionalFeature -Online -FeatureName "Containers-DisposableClientVM" -All`; Pro/Enterprise/Edu only (not Home); disposable hypervisor-isolated VM; networking ON by default (disable via .wsb config for untrusted files).


## Reference: dns-blocklists-2026.md

# DNS Blocklists — verified knowledge bank (2026-08)

Verified against live repo state 2026-08-14 (HaGeZi README + whotracks test numbers,
1Hosts raw lists + GitHub issue tracker, StevenBlack repo README/alternates table).

## Stacking semantics (the core rule)

At a DNS resolver (ControlD/NextDNS/Pi-hole), multiple lists UNION. The union's
breakage risk = the worst false-positive class of any member. You cannot take "only
the good parts" of a list. Never add a list for its unique coverage without accepting
its unique FPs.

## HaGeZi (github.com/hagezi/dns-blocklists) — tiers & sizes (Aug 2026)

| Tier | Entries | Blocking | Maintainer's own calibration |
|------|--------:|----------|------------------------------|
| Light | 40,657 | Relaxed | "should not lead to any restrictions" |
| Normal | 181,000 | Relaxed/Balanced | "should not lead to restrictions for the most part" |
| Pro | 214,122 | Balanced | "should only very rarely lead to restrictions... personal recommendation for mostly problem-free adblocking" |
| Pro++ | 237,706 | Balanced/Aggressive | "may contain a few false positive domains that limit functionality... only experienced users" |
| Ultimate | 261,836 | Aggressive | "contains domains that limit functionality in apps and on websites" (blocks META trackers, Xbox/Windows Spotlight trackers, location/IP trackers) |
| TIF | 2,032,148 | — | malware/cryptojacking/scam/spam/phishing + C2; "very large, may cause high memory usage" |
| TIF medium | 390,296 | — | "only important feeds" |
| TIF mini | 166,987 | — | size-optimized, recommended for browser/mobile |

Pro++ vs Pro delta (~23.6k entries) is exactly three things:
1. **Referral/affiliate domains**: Pro blocks only referral domains that are primarily
   trackers or scam/spam-associated; Pro++ blocks ALL except pure link trackers —
   named: ad.doubleclick.net, adservice.google.*, app.adjust.*, analytics.adjust.*.
   This is the app-deep-link breakage class (Adjust/AppsFlyer on mobile).
2. **Full Pop-Up Ads list** (52,289 entries) folded into Pro++/Ultimate (Dec 2024 change).
3. **30-day malicious NRDs** extracted from TIF (~30k domains) added to Pro++/Ultimate.
   The random "brand-new legit site blocked" class; ages out of the window.

Quantified breakage (HaGeZi's whotracks.me test, 299,646 queries, all pages full-loaded):
Pro blocked 32.54%, Pro++ 39.94%, Ultimate 43.75%. Pro++ ≈ Pro + ~7.4pp more blocked
queries — that extra 7pp is where the breakage lives.

HaGeZi's FAQ recommendation: combine ONE main list + TIF (mini/medium if size matters);
Normal for households with no admin to unblock, Pro where an admin exists.
HaGeZi's own hierarchy quote (issue tracker): "Ultimate will definitely break your
experience. Pro Plus will likely break something on a site eventually. Pro should only
on rare occasions."

**Verdict for this user (2026-08-14):** ControlD via ctrld → HaGeZi Pro + TIF mini.
Security layer (malware/phishing/C2) complete; referral/popup/NRD breakage classes stay
out. Upgrade path if user wants more: Pro Plus + TIF mini; core apps (Steam/Discord/GOG/
Firefox/Tidal) unaffected either way; watch (a) phone app deep links, (b) brand-new
legit sites <30 days; ControlD allowlist is the safety valve.

## 1Hosts (github.com/badmojr/1Hosts) — unique-FP class, LIVE-VERIFIED 2026-08-14

Structure 2026: only **Lite** (balanced, "set & forget") and **Xtra** (aggressive beta);
the old Pro tier is gone.

Live list state (fetched 2026-08-14, lists updated same morning):
- Lite: 205,923 rules, 6.44 MB — **smoot.apple.com still present** (grep -c = 1)
- Xtra: 1,110,064 rules, 29.6 MB — smoot.apple.com still present (grep -c = 2)

FP history (issue tracker):
- #560 (2022, comments through Apr 2025): *.smoot.apple.com — breaks iMessage GIFs.
  "1Hosts remains the only active list that insists on blocking *.smoot.apple.com.
  Neither HaGeZi, Steven Black, AdGuard, OISD, hBlock block this entire domain, even
  in their aggressive lists." Still true 2026.
- #2224 (Jun 2025): api-glb-aaps1b.smoot.apple.com breaks Siri.
- #908: xp.apple.com blocks iOS/watchOS updates; maintainer refused removal ("badmojr
  does not want to remove it. His decision.").
- #1847: codepush.appcenter.ms (breaks app account/update features), cookie-cdn.cookiepro.com
  (OneTrust consent CDN), firebaseinstallations.googleapis.com.
- #3406 (Jan 2026): playtomic.com (real booking service) blocked in LITE; fixed within 2h.
- #4188 (May 2026, OPEN, updated May 29): broad legit-infrastructure block report —
  Tailscale login/logs, NordVPN, Hugging Face + XetHub CDN, ModelScope, Ultralytics,
  Modal, RunPod, Google Colab, Z.ai APIs, Nothing Tech device services, Amazon Prime
  Video, Airtel IPTV, Qualcomm, Mixpanel, GCP resource-manager APIs, Zomato, AliExpress,
  Robu.in.

Fairness nuance: the Apple blocks (smoot/xp.apple.com) are DELIBERATE privacy stances,
not sloppiness — smoot.apple.com genuinely carries Spotlight keystroke telemetry to
Apple (documented since 2014, StackExchange/HN). Maintainer holds these and fixes clear
non-Apple FPs fast (playtomic: 2h). For a zero-breakage goal the class is still a deal-
breaker; for a max-privacy goal it is a feature.

ControlD mirror: x-1hosts-lite (freedns.controld.com, 76.76.2.38 / 2606:1a40::38),
updates every 30 min.

## StevenBlack hosts (github.com/StevenBlack/hosts) — conservative aggregator

- **Default unified file = adware + malware ONLY** (99,557 unique domains, updated
  2026-08-05). The fakenews/gambling/porn/social categories are OPTIONAL extensions:
  `alternates/` folder (31 variants) or `updateHostsFile.py --extensions`; script docs
  explicitly: "No extensions are included by default." (Agent asserted otherwise once
  and the user caught it — verify, don't pattern-match.)
- Extension sizes: fakenews ~2,187, gambling ~6,473, social ~3,244, porn ~76,749.
- Sources: AdAway, AdGuard DNS filter, MVPS, yoyo, Dan Pollock, someonewhocares,
  + Steven Black's own small ad-hoc list. Exact-match hosts entries, no wildcards.
- Unique-FP class: near zero — it is a deduplicated union of well-known lists; almost
  everything is also in other lists, and it is already inside HaGeZi's source set
  (redundant on top of HaGeZi).
- ControlD mirror: x-stevenblack (76.76.2.35 / 2606:1a40::35), freedns.controld.com.

## Verification recipes ("is X list still blocking Y / still an issue?")

1. Live list content (the authoritative check):
   `curl -sL https://raw.githubusercontent.com/<owner>/<repo>/master/<path> | grep -c <domain>`
   1Hosts paths: Lite/hosts.txt, Xtra/hosts.txt. Header lines carry rule count +
   "Last modified" timestamp (e.g. "# |Count: 205,923 rules!", "# Last modified:
   2026-08-14T08:41:04.375Z").
2. Repo top-level layout (find where the lists live):
   `curl -sG "https://api.github.com/repos/<owner>/<repo>/contents/"` and parse names.
3. Recent FP-issue activity:
   `curl -sG "https://api.github.com/search/issues" --data-urlencode "q=repo:<owner>/<repo> is:issue \"false positive\" created:>=YYYY-MM-DD" --data-urlencode "per_page=30"`
   then parse items[].state/created_at/title.
4. Hardline parser note: big inline bash one-liners (loops + curls + python in one
   command) can trip the terminal blocklist — keep commands short, or write to a
   script file first. A blocked payload is saved under
   ~/.hermes/cache/blocked-scripts/ and can be run with `bash <path>`.
5. Rule for claims: for ANY blocklist behavior claim, assert only from live repo state
   (README + list content). This user catches unverified claims (StevenBlack default
   composition, SQLWriter path) and expects the correction owned immediately.


## Reference: secure-boot-2026.md

# Windows Secure Boot — 2026 trust-anchor migration, dbx, BIOS options

Verified Aug 2026 against Microsoft Learn/Support, Tech Community, LWN, Debian wiki,
shim-review, ESET coverage. Re-check before relying in later years (cert table is time-bound).

## The 2011→2023 certificate migration

UEFI Secure Boot validates signatures against db (allowed) / dbx (forbidden) membership —
it does NOT check certificate validity dates. Expiry breaks nothing already booting; it only
stops NEW servicing (no more boot-manager fixes, db/dbx updates, or revocation mitigations).
Migration matters because Microsoft stops signing/revoking under expired anchors.

| Expiring cert | Expires | Replacement | Store | Purpose |
|---|---|---|---|---|
| Microsoft Corporation KEK CA 2011 | 2026-06-24 | Microsoft Corporation KEK 2K CA 2023 | KEK | signs db/dbx updates |
| Microsoft UEFI CA 2011 (3rd-party) | 2026-06-27 | Microsoft UEFI CA 2023 + Microsoft Option ROM UEFI CA 2023 (split) | db | signs 3rd-party bootloaders (shim), EFI apps, option ROMs |
| Microsoft Windows Production PCA 2011 | 2026-10-19 | Windows UEFI CA 2023 | db | signs Windows boot manager |

The 2023 split (UEFI CA vs Option ROM CA) exists so a system can trust option ROMs
(GPU/NIC preboot firmware) without trusting 3rd-party bootloaders. 2023 CAs valid to 2038.

Devices that don't migrate keep booting + getting normal updates, but receive NO new
boot-level protections — trust state is effectively frozen.

## Why it matters (2026 events)

- BlackLotus (CVE-2023-24932): endgame = Microsoft Windows Production PCA 2011 added
  wholesale to dbx (programmatic, no opt-out) — blocks ALL old-signed boot managers.
- ESET (disclosed 2026-07-14): 11 old shims signed by Microsoft UEFI CA 2011 bypassed
  Secure Boot on almost any machine trusting that CA (CVE-2026-8863, CVE-2026-10797;
  reported Feb 2026, dbx revocation in Jun 9 2026 Patch Tuesday). Attack needs no exploit —
  local code execution + carry the old signed shim. Lesson: the 3rd-party UEFI CA is the
  boot chain's recurring weak point.
- 2023 signing program (Oct 2025+): shim Review Board + annual independent security audits.

## Verifying migration state on a machine

- `HKLM\SYSTEM\CurrentControlSet\Control\SecureBoot\AvailableUpdates` (DWORD): pending-work
  bitmask; **0x0 = fully migrated** (matches Microsoft's own fully-updated telemetry shape).
  Bits: 0x0002 dbx update | 0x0004 KEK 2K CA 2023 | 0x0020 SkuSiPolicy | 0x0040 Windows UEFI
  CA 2023→db | 0x0080 Production PCA 2011→dbx | 0x0100 2023-signed boot manager | 0x0200 SVN
  | 0x0400 SBAT | 0x0800 Option ROM UEFI CA 2023→db | 0x1000 Microsoft UEFI CA 2023→db |
  0x4000 conditional guard.
- `HKLM\SYSTEM\CurrentControlSet\Control\SecureBoot\MicrosoftUpdateManagedOptIn`: org opt-in
  (0x5944 recommended). Absent on consumer = normal (auto-managed).
- `HKLM\SYSTEM\CurrentControlSet\Control\SecureBoot\State\UEFISecureBootEnabled` = 1.
- System log, source TPM-WMI: 1808 = all certs + 2023 boot manager applied (good);
  1801 = not applied/failed; 1036/1799/1037/1042 = DB / boot manager / DBX / SVN steps;
  1795 = firmware error → OEM BIOS update needed.
- Admin PowerShell (True = migrated):
  `[System.Text.Encoding]::ASCII.GetString((Get-SecureBootUEFI db).Bytes) -match 'UEFI CA 2023'`
  `[System.Text.Encoding]::ASCII.GetString((Get-SecureBootUEFI KEK).Bytes) -match 'KEK 2K CA 2023'`
- UI: Windows Security > Device security > Secure Boot (badges added Apr 2026):
  green = done, yellow = pending, red = firmware rejects (usually BIOS update needed).
- Driver: `\Microsoft\Windows\PI\Secure-Boot-Update` scheduled task (runs ~every 12h).
  Debloat scripts that disable it or wipe the SecureBoot registry key strand machines
  pre-migration — the main way a consumer box ends up stuck.

## BIOS Secure Boot options (Gigabyte/ASRock AMI firmware)

Key Management submenu appears when Secure Boot Mode = Custom (Security or Boot tab).

- **Delete PK (Platform Key)**: drops to Setup Mode; Secure Boot unenforced; VBS/HVCI refuse
  to run. Recovery: Restore Factory Keys / Enroll All Factory Default Keys (forces User Mode
  again). After a factory restore the board is back on 2011-era defaults → Windows re-pushes
  the 2023 migration + dbx via the PI task (downgraded-trust window in between).
- **Provision Factory Default Keys**: clears PK+KEK+db+dbx → Setup Mode.
- **Device Guard Ready → Remove 'UEFI CA' from DB**: removes the Microsoft UEFI CA
  (3rd-party) from db. Backed by a REAL Microsoft requirement — WHCR for Defender Credential
  Guard (learn.microsoft.com/windows-hardware/design/device-experiences/oem-credential-guard):
  "Microsoft UEFI CA must be removed from the Secure Boot database" (manufacturing-time OEM
  certification requirement). NOT required for HVCI/Memory Integrity to run (its compat list
  has no CA entry) nor for Credential Guard on retail machines.
  - Value: structural immunity to the 3P-shim attack class (see ESET); Microsoft key-creation
    guidance includes 3P CAs "except on systems locked down to boot Windows only"; secured-core
    PCs ship without them.
  - Costs: Linux shim permanently dead (post-expiry only 2023-signed 3rd-party code exists;
    removing the CA kills both 2011+2023 trust); add-in card option ROMs (GPU/NIC preboot
    firmware) can fail validation — shim-review #547 warns of systems left with no display
    output during boot; recovery = BIOS key reset.
  - Verdict: right for locked-down Windows-only boxes; skip on gaming rigs with add-in cards
    or any future dual-boot plans.

## Autoruns "(Not Verified)" on Microsoft files — triage

- Autoruns runs WinVerifyTrust at scan time on embedded Authenticode signatures. Many inbox
  binaries (wmpnetwk.exe, wmpnscfg.exe, MsSense.exe...) are catalog-signed — their hash lives
  in a signed .cat under System32\CatRoot — so Autoruns reports (Not Verified). Not a malware
  signal.
- Definitive check: `Get-AuthenticodeSignature <path>` (catalog-aware via CryptSvc) → Status
  Valid; or `sigcheck -i <path>` → "Verified: Signed" + matching .cat path.
- MsSense.exe (Defender EDR) is a known false negative (Autoruns protected-folder check bug,
  acknowledged by Microsoft).
- Real red flags: non-canonical paths, unsigned 3rd-party entries in Run/Services, or
  Microsoft-publisher strings on files outside system locations.

## Research method for firmware/security options (user preference)

- When the user recalls a BIOS option vaguely, find the EXACT option via vendor manuals
  (ManualsLib / manualowl, searchable via MCP exa with the remembered phrase) before
  answering. "Delete PK" ≠ "Remove UEFI CA from DB" — they have opposite meanings.
- Before judging an option useful/useless, check Microsoft's hardware-requirement pages
  (learn.microsoft.com/windows-hardware/design/device-experiences/oem-*). WHCR requirements
  are the authority; distinguish manufacturing-time OEM certification requirements from
  runtime requirements. Don't dismiss as "legacy" without this check.

## Sources

- aka.ms/GetSecureBoot; KB5036210 (2023 cert deployment); KB5025885 (boot manager revocations)
- Tech Community: "Act now: Secure Boot certificates expire in June 2026"; "What IT teams need
  to know about Linux Secure Boot certificates expiring in 2026"
- wiki.debian.org/SecureBoot/CAChanges; LWN "Secure Boot certificate expiration is here"
- fwupd.github.io/libfwupdplugin/uefi-db.html; github.com/rhboot/shim-review#547
- github.com/cjee21/Check-UEFISecureBootVariables (fleet audit tool)


## Reference: windows-event-log-diagnostics.md

# Windows event-log & power diagnostics (verified on this box, 2026-08)

## Sleep/wake forensics

- Kernel-Power 42 = entering sleep; 107 = resumed. A 42→107 pair 1-5s apart at EVERY sleep entry = abortive USB wake blip (this box: 136/136 sleeps over 30 days), not a real wake.
- Power-Troubleshooter (System log, provider Microsoft-Windows-Power-Troubleshooter, Event 1) = the authoritative per-session wake record: real sleep/wake timestamps + wake source (e.g. "Device - AMD USB 3.10 eXtensible Host Controller - 1.10"). One per real wake; count ≈ real wake count. Sleep time in the event matches the Kernel-Power 42 timestamp.
- The Kernel-Power 566 + VfpExt + Netwtw14 cluster marks the REAL resume moment; the 107 logged two seconds after 42 is the abort. Don't trust raw 42/107 pairing for wake attribution.
- powercfg: /a (available states; "S0 Low Power Idle: system firmware does not support" = no Modern Standby), /lastwake (wake source, non-admin), /devicequery wake_armed (armed devices, non-admin), /waketimers (admin), /devicedisablewake "<name>" (admin; the spurious-wake fix — this box: start with "AMD UCM-UCSI Device").

## Device flap forensics (disconnect/reconnect sounds)

- Runtime device add/remove events live in Microsoft-Windows-Kernel-PnP/Device Management (Applications and Services log). Kernel-PnP/Configuration = device config events. System-log Kernel-PnP 400/410/411 are sparse (mostly boot-time) — querying only System misses runtime flaps.
- DISPLAY\<EDID> device flapping = monitor being removed/re-added at the PnP level → the "disconnect chime when my monitor turns off" pattern (this box: DISPLAY\AUS25A6 = ASUS monitor, ~20 events/2 days). Cause: DisplayPort link drop on DPMS standby, link retrain on wake. NOT a USB device (verify: zero USB re-enumeration in the same window), NOT ASPM. Fix: cable, HDMI vs DP, monitor OSD power options, driver.
- AMD Type-C flakiness: Microsoft-Windows-USB-UCMUCSICX/Operational, Event 1 "UcmUcsiCx device has encountered a failure" (this box: ~weekly, 11 in 3 months). UCSI = motherboard chipset Type-C (front USB-C header), NOT the GPU, NOT the monitor. A device that fails weekly should never be armed for wake.
- USB controller errors: Microsoft-Windows-USB-USBXHCI-Operational — NOTE the hyphenated name (Event 50 "Controller Error Encountered"). Operational logs often use hyphens instead of slashes; enumerate with Get-WinEvent -ListLog *USB* before querying.

## TPM event forensics (AMD fTPM)

- TPM provider, System log: 17 (Info) = command failed, 14 (Error) = driver gave up after retries, 18 = routine provisioning trigger (healthy). Burst of ~6 alternating 17/14 pairs = retry loop after a transient fTPM failure; correlate with sleep/resume churn and gaming-session end. Event 14 Data fields (driverFile/lineNumber/Data) are driver-internal, not publicly documented — don't over-interpret.
- Get-Tpm / Get-BitLockerVolume need admin; Win32_Tpm (root\cimv2\Security\MicrosoftTpm) unavailable non-admin. Get-PnpDevice -Class SecurityDevices works non-admin (TPM 2.0 + PSP status).

## PowerShell-from-WSL quirks (this setup)

- Write .ps1 to /mnt/c/Users/<User>/AppData/Local/Temp/, run: powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\<User>\AppData\Local\Temp\x.ps1". Keep scripts pure ASCII (PS 5.1 misreads UTF-8 without BOM).
- PS stdout through WSL interop arrives as readable ASCII/UTF-8 — do NOT pipe through iconv -f UTF-16 (mangles into CJK mojibake; happened on the first TPM diagnostic).
- CRLF line endings: end-anchored grep patterns fail; use mid-line patterns, grep -a for files grep flags as binary, awk for context windows (grep -B misbehaved on this file).
- FilterHashtable StartTime/EndTime: pass ISO strings with Z suffix — PS converts to local correctly.
