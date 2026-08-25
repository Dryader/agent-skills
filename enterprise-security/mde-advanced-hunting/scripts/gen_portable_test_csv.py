#!/usr/bin/env python3
"""Synthetic fixture generator for the portable-app discovery pipeline (v3.3).

Run from WSL:  python3 gen_portable_test_csv.py
Writes under /mnt/c/Users/<user>/Downloads:
  portable-test-input.csv  — 7 rows covering every v3.3 flag/bucket branch (47 cols)
  portable-test-prev.csv   — previous-run file (growth + decision carry-over)

Then run:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File \
    'C:/Users/<user>/Downloads/portable-app-discovery.ps1' \
    -InputCsv 'C:/Users/<user>/Downloads/portable-test-input.csv' \
    -OutputCsv 'C:/Users/<user>/Downloads/portable-test-out.csv' \
    -PreviousCsv 'C:/Users/<user>/Downloads/portable-test-prev.csv'

Expected (current v3.17 code; see the SKILL.md portable-app-discovery section):
  buckets 2 Loud / 2 RedFlagged / 1 Internal / 1 Installer / 1 Stable;
  AAA111 rf=0 Internal (suppression), BBB222 rf=0 SIGNED_PREVALENT + Decision=Allow
  carried, CCC333 rf=10 T2 B7 C1 Loud (the svchost.exe name now trips SYSTEM_NAMED —
  the old "rf=9" anchor predates it), DDD444 Installer, EEE555 rf=2 Loud
  (RENAMED_LOLBIN), FFF666 rf=2 RedFlagged NETWORK_SHARE, GGG777 rf=3 RedFlagged
  OFFICE_DROP.
"""
import csv, os

OUT = "/mnt/c/Users/<user>/Downloads"

cols = ["SHA1","FileName","FolderPath","PathCategory","DeviceCount","UserCount","DistinctDays","ExecutionCount",
        "ScriptLaunches","SystemLaunches","ExplorerLaunches","InstallerLaunches",
        "CompanyName","ProductName","OriginalFileName","ProcessIntegrityLevel","ParentProcess","ExampleCommandLine",
        "Departments","TopFolderPath","InTvmInventory","SmartScreenVerdict","DefenderAlerts","IsMalwareAlert",
        "NetworkConnections","IsSigned","IsTrusted","Signer","PersistenceDetected","IsAITool","NonStandardPorts",
        "SideloadedUnsignedDlls","VersionCount","BundleMembers","FirstSeenAny","ExampleOriginUrl","ExampleInitiator",
        "ExampleInitiatorClass","GlobalPrevalence","ProfileAvailability","IsCertificateValid","ThreatName",
        "UsersSample","IsUnknown","Confidence","IsInstaller","IsInternalTool"]

rows = [
    # A: internal tool — unsigned + fleet-narrow is EXPECTED: rf=0, INTERNAL_UNSIGNED
    dict(SHA1="AAA111", FileName="healthcheck.exe", FolderPath=r"C:\Users\<user>\AppData\Local\Programs\HealthCheck\healthcheck.exe",
         PathCategory="AppDataLocalPrograms", DeviceCount="5", UserCount="5", DistinctDays="40", ExecutionCount="120",
         ScriptLaunches="0", SystemLaunches="2", ExplorerLaunches="118", InstallerLaunches="0",
         CompanyName="Contoso IT", OriginalFileName="healthcheck.exe", ProcessIntegrityLevel="Medium",
         ExampleCommandLine="healthcheck.exe -scan", TopFolderPath=r"C:\Users\<user>\AppData\Local\Programs\HealthCheck",
         InTvmInventory="False", IsSigned="False", IsTrusted="False", Signer="",
         PersistenceDetected="False", IsAITool="False", NonStandardPorts="False", SideloadedUnsignedDlls="",
         VersionCount="1", BundleMembers="2", FirstSeenAny="2026-01-15T00:00:00Z",
         ExampleOriginUrl="", ExampleInitiator="explorer.exe", ExampleInitiatorClass="Explorer",
         GlobalPrevalence="80", ProfileAvailability="Available", IsCertificateValid="False", ThreatName="",
         UsersSample='["j@contoso.com"]', IsUnknown="True", Confidence="ProvenanceConfirmed",
         IsInstaller="False", IsInternalTool="True"),
    # B: signed + globally prevalent + clean -> SIGNED_PREVALENT, rf=0
    dict(SHA1="BBB222", FileName="mouseclicker.exe", FolderPath=r"C:\Users\<user>\Downloads\mouseclicker.exe",
         PathCategory="Downloads", DeviceCount="42", UserCount="38", DistinctDays="25", ExecutionCount="900",
         ScriptLaunches="0", SystemLaunches="0", ExplorerLaunches="900", InstallerLaunches="0",
         CompanyName="ClickSoft LLC", OriginalFileName="mouseclicker.exe", ProcessIntegrityLevel="Medium",
         ExampleCommandLine="mouseclicker.exe", TopFolderPath=r"C:\Users\<user>\Downloads",
         InTvmInventory="False", IsSigned="True", IsTrusted="True", Signer="DigiCert",
         PersistenceDetected="False", IsAITool="False", NonStandardPorts="False", SideloadedUnsignedDlls="",
         VersionCount="1", BundleMembers="1", FirstSeenAny="2026-05-02T00:00:00Z",
         ExampleOriginUrl="https://clicky.example/mouseclicker.exe", ExampleInitiator="msedge.exe", ExampleInitiatorClass="Browser",
         GlobalPrevalence="500000", ProfileAvailability="Available", IsCertificateValid="True", ThreatName="",
         UsersSample='["a@contoso.com"]', IsUnknown="False", Confidence="ProvenanceConfirmed",
         IsInstaller="False", IsInternalTool="False"),
    # C: payload — every red flag: rf=9, RedFlagged
    dict(SHA1="CCC333", FileName="svchost.exe", FolderPath=r"C:\Users\<user>\AppData\Local\Temp\svchost.exe",
         PathCategory="Temp", DeviceCount="3", UserCount="2", DistinctDays="4", ExecutionCount="9",
         ScriptLaunches="3", SystemLaunches="0", ExplorerLaunches="0", InstallerLaunches="0",
         CompanyName="", OriginalFileName="cmd.exe", ProcessIntegrityLevel="Low",
         ExampleCommandLine="powershell -enc Zm9v", TopFolderPath=r"C:\Users\<user>\AppData\Local\Temp",
         InTvmInventory="False", IsSigned="False", IsTrusted="False", Signer="",
         PersistenceDetected="True", IsAITool="False", NonStandardPorts="True", SideloadedUnsignedDlls="evil.dll",
         VersionCount="1", BundleMembers="1", FirstSeenAny="2026-07-20T00:00:00Z",
         ExampleOriginUrl="", ExampleInitiator="outlook.exe", ExampleInitiatorClass="Email",
         GlobalPrevalence="50", ProfileAvailability="Available", IsCertificateValid="False", ThreatName="",
         UsersSample='["v@contoso.com"]', IsUnknown="True", Confidence="ProvenanceConfirmed",
         IsInstaller="False", IsInternalTool="False"),
    # D: installer — signed, in prev run: bucket Installer
    dict(SHA1="DDD444", FileName="FirefoxSetup.exe", FolderPath=r"C:\Users\<user>\Downloads\FirefoxSetup.exe",
         PathCategory="Downloads", DeviceCount="60", UserCount="55", DistinctDays="1", ExecutionCount="60",
         ScriptLaunches="0", SystemLaunches="0", ExplorerLaunches="60", InstallerLaunches="0",
         CompanyName="Mozilla Corporation", OriginalFileName="setup.exe", ProcessIntegrityLevel="Medium",
         ExampleCommandLine="FirefoxSetup.exe", TopFolderPath=r"C:\Users\<user>\Downloads",
         InTvmInventory="True", IsSigned="True", IsTrusted="True", Signer="Mozilla Corporation",
         PersistenceDetected="False", IsAITool="False", NonStandardPorts="False", SideloadedUnsignedDlls="",
         VersionCount="1", BundleMembers="1", FirstSeenAny="2026-07-01T00:00:00Z",
         ExampleOriginUrl="https://download.mozilla.org/firefox", ExampleInitiator="msedge.exe", ExampleInitiatorClass="Browser",
         GlobalPrevalence="1000000", ProfileAvailability="Available", IsCertificateValid="True", ThreatName="",
         UsersSample='["b@contoso.com"]', IsUnknown="False", Confidence="ExecutionOnly",
         IsInstaller="True", IsInternalTool="False"),
    # E: renamed LOLBin, unsigned -> rf=2 (UNSIGNED + RENAMED_LOLBIN)
    dict(SHA1="EEE555", FileName="notvirus.exe", FolderPath=r"C:\Users\<user>\Desktop\notvirus.exe",
         PathCategory="Desktop", DeviceCount="1", UserCount="1", DistinctDays="2", ExecutionCount="2",
         ScriptLaunches="0", SystemLaunches="0", ExplorerLaunches="2", InstallerLaunches="0",
         CompanyName="", OriginalFileName="cmd.exe", ProcessIntegrityLevel="Medium",
         ExampleCommandLine="notvirus.exe /c whoami", TopFolderPath=r"C:\Users\<user>\Desktop",
         InTvmInventory="False", IsSigned="False", IsTrusted="False", Signer="",
         PersistenceDetected="False", IsAITool="False", NonStandardPorts="False", SideloadedUnsignedDlls="",
         VersionCount="1", BundleMembers="1", FirstSeenAny="2026-06-10T00:00:00Z",
         ExampleOriginUrl="", ExampleInitiator="explorer.exe", ExampleInitiatorClass="Explorer",
         GlobalPrevalence="5000", ProfileAvailability="Available", IsCertificateValid="False", ThreatName="",
         UsersSample='["c@contoso.com"]', IsUnknown="False", Confidence="ProvenanceConfirmed",
         IsInstaller="False", IsInternalTool="False"),
    # F: UNC share execution -> NETWORK_SHARE flag, rf=2
    dict(SHA1="FFF666", FileName="portaltool.exe", FolderPath=r"\\filesrv01\shares\portables\portaltool.exe",
         PathCategory="NetworkShare", DeviceCount="12", UserCount="10", DistinctDays="15", ExecutionCount="40",
         ScriptLaunches="1", SystemLaunches="0", ExplorerLaunches="39", InstallerLaunches="0",
         CompanyName="", OriginalFileName="portaltool.exe", ProcessIntegrityLevel="Medium",
         ExampleCommandLine="portaltool.exe", TopFolderPath=r"\\filesrv01\shares\portables",
         InTvmInventory="False", IsSigned="False", IsTrusted="False", Signer="",
         PersistenceDetected="False", IsAITool="False", NonStandardPorts="False", SideloadedUnsignedDlls="",
         VersionCount="1", BundleMembers="4", FirstSeenAny="2026-03-01T00:00:00Z",
         ExampleOriginUrl="", ExampleInitiator="explorer.exe", ExampleInitiatorClass="Other",
         GlobalPrevalence="3000", ProfileAvailability="Available", IsCertificateValid="False", ThreatName="",
         UsersSample='["d@contoso.com"]', IsUnknown="False", Confidence="ExecutionOnly",
         IsInstaller="False", IsInternalTool="False"),
    # G: macro drop -> rf=3 (UNSIGNED + LOW_PREVALENCE + TEMP_EXECUTION), OFFICE_DROP flag
    dict(SHA1="GGG777", FileName="invoice_open.exe", FolderPath=r"C:\Users\<user>\AppData\Local\Temp\invoice_open.exe",
         PathCategory="Temp", DeviceCount="1", UserCount="1", DistinctDays="1", ExecutionCount="1",
         ScriptLaunches="0", SystemLaunches="0", ExplorerLaunches="0", InstallerLaunches="0",
         CompanyName="", OriginalFileName="invoice_open.exe", ProcessIntegrityLevel="Low",
         ExampleCommandLine="invoice_open.exe", TopFolderPath=r"C:\Users\<user>\AppData\Local\Temp",
         InTvmInventory="False", IsSigned="False", IsTrusted="False", Signer="",
         PersistenceDetected="False", IsAITool="False", NonStandardPorts="False", SideloadedUnsignedDlls="",
         VersionCount="1", BundleMembers="1", FirstSeenAny="2026-07-28T00:00:00Z",
         ExampleOriginUrl="", ExampleInitiator="winword.exe", ExampleInitiatorClass="OfficeMacro",
         GlobalPrevalence="30", ProfileAvailability="Available", IsCertificateValid="False", ThreatName="",
         UsersSample='["p@contoso.com"]', IsUnknown="True", Confidence="ProvenanceConfirmed",
         IsInstaller="False", IsInternalTool="False"),
]

assert len(cols) == 47, f"column count drift: {len(cols)}"
for i, r in enumerate(rows):
    assert len(r) <= len(cols), f"row {i} has {len(r)} fields, expected <= {len(cols)}"

with open(os.path.join(OUT, "portable-test-input.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({c: r.get(c, "") for c in cols})

prev_cols = ["SHA1", "DeviceCount", "UserCount", "Decision"]
prev = [
    dict(SHA1="DDD444", DeviceCount="58", UserCount="54", Decision=""),
    dict(SHA1="BBB222", DeviceCount="40", UserCount="36", Decision="Allow"),
    dict(SHA1="CCC333", DeviceCount="2", UserCount="2", Decision="Quarantine"),
]
with open(os.path.join(OUT, "portable-test-prev.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=prev_cols)
    w.writeheader()
    for r in prev:
        w.writerow(r)

print(f"wrote portable-test-input.csv (7 rows, {len(cols)} cols) + portable-test-prev.csv under {OUT}")
