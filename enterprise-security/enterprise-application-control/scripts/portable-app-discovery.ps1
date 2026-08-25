<#
.SYNOPSIS
    Portable app DISCOVERY — no scores. Facts + flags + a plain red-flag tally.
    The old Portability/Risk 0-10 composites were dropped: weighted scores
    overfit the analyst's intuition and misled (signed+prevalent shadow IT
    scored 0). What remains is what was actually being used:

      - Raw fact columns (signed, trust, prevalence, vendor, path, users...)
      - Boolean flags (PERSISTENCE, SCRIPT_LAUNCHED, RENAMED_LOLBIN, ...)
      - RedFlagCount: an UNWEIGHTED tally of independent red-flag booleans.
        "How many reasons to look" is a count, not a judgment. Sort by it.
      - Buckets: Loud (threat-shaped signal) / RedFlagged (count >= 2) /
        Internal / New / Installer / Stable
      - Decision carry-over from PreviousCsv (vet once, track state)
      - Growth KPI vs PreviousCsv (the shadow-IT governance signal)

    Input:  CSV from provenance-full.kql (MDE Advanced Hunting export).
    Output: <OutputCsv> (all) + <base>-redflagged.csv (review list).

    v3.1: readability without lying — Families vector ("T2 B3 C1", a partition
        of RedFlagCount), LoudSignal tier (documented threat-shaped flag list),
        Profile string (Trust · Prevalence · Age categorical bands).
    v3.15: DRIVER_LOADED flag (kernel driver loaded by the candidate — KQL
        ActorBehaviorEvents DriverLoads column, red/Behavior/not loud). LoudSignal
        list documented here (must match $loud=$true sites in Get-Flags):
        MALWARE_HIT, ALERT_HIT, PERSISTENCE, RENAMED_LOLBIN, ENCODED_CMD,
        DOWNLOAD_CRADLE, ASR_VERDICT, WMI_PERSISTENCE, STARTUP_LNK, SELF_DELETED,
        DPAPI_ACCESS, SYSTEM_NAMED, SENSITIVE_READ, DEFENDER_TAMPERING.
    v3.17: DEFENDER_TAMPERING flag (KQL ActorBehaviorEvents DefenderTamperHits —
        TamperingAttempt, T1562.001 — candidate tried to change Defender XDR
        settings; red/Behavior/LOUD). No other logic changes.
    NOTE: the DriverLoads / DefenderTamperHits columns are produced by the full
        pipeline's KQL (live environment); the committed provenance kqls don't
        compute them — these flags are $has*-guarded and degrade gracefully.
    v3.16: CSV reads are now explicit -Encoding UTF8 (PS 5.1 Import-Csv defaults
        to ANSI — a UTF-8 no-BOM export would mojibake non-ASCII file names and
        company names; BOM'd exports were already handled by BOM detection).
        No flag/logic changes.
    v3: scores dropped; RedFlagCount; buckets; new fact columns
        (PathCategory, launcher counts, IsInstaller, IsInternalTool);
        internal tools suppress expected flags (unsigned/low-prevalence)
        but keep INTERNAL_UNSIGNED as the "should be signed" finding.
    v2.2: Confidence (ProvenanceConfirmed/ExecutionOnly) + IsUnknown carried.
    v2.1: SIDELOAD_DLL re-weighted to +1 (historical; flag-only now).
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$InputCsv,
    [string]$OutputCsv = ".\portable-apps.csv",
    [string]$PreviousCsv    # optional: previous run's CSV for growth + decision carry-over
)

$ErrorActionPreference = "Stop"
Write-Host "=== Portable App Discovery (flags, no scores) ===" -ForegroundColor Cyan

# =============================================================================
# 1. LOAD
# =============================================================================
if (-not (Test-Path $InputCsv)) { throw "Not found: $InputCsv" }
$data = @(Import-Csv $InputCsv -Encoding UTF8)   # @() so single-row CSVs behave like arrays (Count, [0])
Write-Host "[LOAD] $($data.Count) candidates"

# Previous run: growth trend (the #1 shadow IT governance KPI)
# + decision carry-over: same SHA1 in the previous run keeps its verdict
$prevDevices = @{}
$prevDecisions = @{}
if ($PreviousCsv) {
    if (-not (Test-Path $PreviousCsv)) { throw "PreviousCsv not found: $PreviousCsv" }
    $prev = Import-Csv $PreviousCsv -Encoding UTF8
    foreach ($p in $prev) {
        $hk = if ($p.SHA1) { $p.SHA1 } elseif ($p.SHA256) { $p.SHA256 } else { "" }
        if ($hk) {
            $prevDevices[$hk] = @{ Devices = try { [int]$p.DeviceCount } catch { 0 };
                                   Users  = try { [int]$p.UserCount } catch { 0 } }
            if ($p.Decision) { $prevDecisions[$hk] = [string]$p.Decision }
        }
    }
    Write-Host "[TREND] $($prevDevices.Count) files from previous run"
}

$columns = $data[0].PSObject.Properties.Name
$hashCol = if ($columns -contains "SHA1") { "SHA1" } else { "SHA256" }

$hasCertCols       = ($columns -contains "IsSigned") -and ($columns -contains "IsTrusted")
$hasFileProfile    = ($columns -contains "GlobalPrevalence") -and ($columns -contains "ProfileAvailability")
# provenance-full.kql aliases these (ExampleOriginUrl/ExampleInitiator); the lean
# provenance.kql emits the raw names — accept both
$hasOriginUrl      = ($columns -contains "FileOriginUrl") -or ($columns -contains "ExampleOriginUrl")
$hasInitiator      = ($columns -contains "InitiatingProcessFileName_Create") -or ($columns -contains "ExampleInitiator")
$hasIntegrityLevel = $columns -contains "ProcessIntegrityLevel"
$hasTvmVisible     = $columns -contains "InTvmInventory"
$hasSmartScreen    = $columns -contains "SmartScreenVerdict"
$hasAlerts         = $columns -contains "DefenderAlerts"
$hasNetwork        = $columns -contains "NetworkConnections"
$hasParentChain    = $columns -contains "ParentProcess"
$hasCommandLine    = $columns -contains "ExampleCommandLine"
$hasLaunchers      = ($columns -contains "ScriptLaunches") -and ($columns -contains "SystemLaunches") `
                     -and ($columns -contains "ExplorerLaunches") -and ($columns -contains "InstallerLaunches")
$hasPathCategory   = $columns -contains "PathCategory"
$hasInstallerCol   = $columns -contains "IsInstaller"
$hasInternalCol    = $columns -contains "IsInternalTool"
$hasFilesCreated   = $columns -contains "FilesCreated"
$hasAsr            = $columns -contains "AsrUntrustedHits"
$hasTvmEv          = $columns -contains "InTvmFileEvidence"
$hasRmm            = $columns -contains "IsRmmTool"
$hasRemoteLaunch   = $columns -contains "RemoteLaunchHits"
$hasSvcs           = $columns -contains "ServicesInstalled"
$hasWmi            = $columns -contains "WmiPersistenceHits"
$hasStartup        = $columns -contains "StartupFilesCreated"
$hasRawIp          = $columns -contains "RawIpConnections"
$hasAv             = $columns -contains "AvDetections"
$hasSensRead       = $columns -contains "SensitiveFileReads"
$hasTamper         = $columns -contains "ProcessTamperingHits"
$hasTimes          = $columns -contains "TimestampStomps"
$hasSelfDel        = $columns -contains "SelfDeletes"
$hasLnk            = $columns -contains "ShellLinksCreated"
$hasDpapi          = $columns -contains "DpapiAccesses"
$hasDriverLoad     = $columns -contains "DriverLoads"
$hasDefenderTamper = $columns -contains "DefenderTamperHits"

Write-Host "[COLS] Cert=$hasCertCols FileProf=$hasFileProfile Origin=$hasOriginUrl Initiator=$hasInitiator"
Write-Host "       Launchers=$hasLaunchers PathCat=$hasPathCategory Installer=$hasInstallerCol Internal=$hasInternalCol FilesCreated=$hasFilesCreated Asr=$hasAsr TvmEv=$hasTvmEv Rmm=$hasRmm RemoteLaunch=$hasRemoteLaunch Svcs=$hasSvcs Wmi=$hasWmi Startup=$hasStartup RawIp=$hasRawIp Av=$hasAv SensRead=$hasSensRead Tamper=$hasTamper Times=$hasTimes SelfDel=$hasSelfDel Lnk=$hasLnk Dpapi=$hasDpapi DriverLoad=$hasDriverLoad DefenderTamper=$hasDefenderTamper"

# Fill missing columns
foreach ($col in @("DistinctDays","DeviceCount")) {
    if (-not ($columns -contains $col)) {
        foreach ($row in $data) { if ($null -eq $row.$col) { $row | Add-Member -NotePropertyName $col -NotePropertyValue 1 -Force } }
    }
}

# =============================================================================
# 2. FLAGS + RED-FLAG TALLY (unweighted — one point per independent signal)
# =============================================================================
$lolbins = @('cmd.exe','powershell.exe','pwsh.exe','rundll32.exe','mshta.exe','certutil.exe','wscript.exe',
             'cscript.exe','regsvr32.exe','msbuild.exe','psexec.exe','bitsadmin.exe','wmic.exe','msiexec.exe',
             'schtasks.exe','reg.exe','sc.exe','net.exe','net1.exe','whoami.exe','taskkill.exe','systeminfo.exe')
# system DLLs found next to executables = search-order-hijack shims (T1574.001)
$hijackDlls = @('version.dll','winmm.dll','ws2_32.dll','cryptbase.dll','d3d9.dll','dwmapi.dll','netapi32.dll',
                'wininet.dll','wldap32.dll','bcrypt.dll','dbghelp.dll','amsi.dll','winhttp.dll','secur32.dll',
                'userenv.dll','iphlpapi.dll','setupapi.dll','cryptsp.dll','wintrust.dll','dsound.dll','mfplat.dll',
                'propsys.dll','uxtheme.dll','dnsapi.dll','rpcrt4.dll','advapi32.dll','ole32.dll','shell32.dll')
# system binaries that must NEVER execute from user-writable paths (masquerade)
$systemBinaries = @('svchost.exe','lsass.exe','csrss.exe','services.exe','smss.exe','winlogon.exe','wininit.exe',
                    'lsaiso.exe','fontdrvhost.exe','dwm.exe','conhost.exe','taskhostw.exe','spoolsv.exe',
                    'msmpeng.exe','searchindexer.exe','dllhost.exe','sihost.exe','lsm.exe','audiodg.exe')
$spoofableVendors = @("microsoft corporation","microsoft","google llc","google inc",
                      "adobe inc","adobe systems","apple inc","oracle america")

function Get-Flags {
    param($row)
    # returns @{ Flags; Red; T; B; C; Loud } — T+B+C == Red (the family
    # vector is a partition of the tally, so it can't lie either)
    $f = [System.Collections.Generic.List[string]]::new()
    $red = 0
    $t = 0; $b = 0; $c = 0   # families: Trust / Behavior / Context
    $loud = $false            # threat-shaped signals (documented list below)
    $isInternal = ($row.IsInternalTool -eq "True")

    # ---- signing / trust (facts from DeviceFileCertificateInfo) ----
    $signed  = ($row.IsSigned -eq "True")
    $trusted = ($row.IsTrusted -eq "True")
    if ($row.IsTrusted -eq "Mixed") { $f.Add("TRUST_MIXED") }
    # unsigned (or no cert row at all) is the baseline red flag — EXCEPT for
    # internal tools, where unsigned is the expected (broken) state and the
    # finding is INTERNAL_UNSIGNED, not a red flag
    if (-not $signed) {
        $f.Add("UNSIGNED")
        if (-not $isInternal) { $red++; $t++ }
    }
    if ($isInternal -and -not $signed) { $f.Add("INTERNAL_UNSIGNED") }

    # ---- global prevalence (FileProfile) ----
    if ($hasFileProfile -and $row.ProfileAvailability -eq "Available") {
        $gp = try { [int64]$row.GlobalPrevalence } catch { 0 }
        if ($row.ThreatName) {
            $f.Add("MALWARE_HIT"); $red++; $b++; $loud = $true   # known malware — the loudest signal
        } elseif ($gp -lt 100 -and -not $signed) {
            $f.Add("LOW_PREVALENCE")
            if (-not $isInternal) { $red++; $t++ } # internal tools are fleet-narrow by nature
        }
    }

    # ---- execution origin (launcher counts from KQL) ----
    if ($hasLaunchers) {
        $sL = try { [int]$row.ScriptLaunches } catch { 0 }
        $yL = try { [int]$row.SystemLaunches } catch { 0 }
        $eL = try { [int]$row.ExplorerLaunches } catch { 0 }
        $iL = try { [int]$row.InstallerLaunches } catch { 0 }
        if ($sL -gt 0) { $f.Add("SCRIPT_LAUNCHED"); $red++; $b++ }
        if ($yL -gt 0) { $f.Add("SYSTEM_LAUNCHED") }   # auto-start flavor — note, not tally
        if ($iL -gt 0) { $f.Add("INSTALLER_ORIGIN") }
    }

    # ---- path category (facts) ----
    if ($hasPathCategory) {
        switch ($row.PathCategory) {
            "Temp"              { $f.Add("TEMP_EXECUTION"); $red++; $c++ }
            "Public"            { $f.Add("PUBLIC_STAGING") }
            "Choco"             { $f.Add("CHOCO_MANAGED") }          # package-manager shims (choco)
            "Scoop"             { $f.Add("SCOOP_MANAGED") }          # user-level package manager
            "PortableAppsFolder"{ $f.Add("PORTABLEAPPS") }           # classic portable convention folder
            "PortableLauncher"  { $f.Add("PORTABLE_LAUNCHER") }      # *Portable.exe platform-format launcher
            "ProgramData"       { $f.Add("PROGRAMDATA_STAGING") }
            "NetworkShare"      { $f.Add("NETWORK_SHARE") }
            "NonSystemDrive"    { $f.Add("USB_EXECUTION") }
        }
    }

    # ---- RMM / remote access tool (T1219) — red flag: a portable RMM tool is
    # review-worthy by definition (remote access = high-impact governance) ----
    if ($hasRmm -and $row.IsRmmTool -eq "True") { $f.Add("RMM_TOOL"); $red++; $c++ }

    # ---- remote launch via PsExec/WMI (ASR d1e49aac) — context, flag-only ----
    if ($hasRemoteLaunch) {
        $rl = try { [int]$row.RemoteLaunchHits } catch { 0 }
        if ($rl -gt 0) { $f.Add("REMOTE_LAUNCHED") }
    }

    # ---- ASR verdicts (rules 01443614/b2b3f03d/56a46372/d1e49aac in
    # audit/block): Microsoft's own verdicts for this file — untrusted /
    # abused-system-tool / WMI-persistence / psexec-wmi-child ----
    if ($hasAsr) {
        $ah = try { [int]$row.AsrUntrustedHits } catch { 0 }
        if ($ah -gt 0) { $f.Add("ASR_VERDICT"); $red++; $t++; $loud = $true }
    }

    # ---- service installation (event 4697) — persistence mechanism ----
    if ($hasSvcs) {
        $sv = try { [int]$row.ServicesInstalled } catch { 0 }
        if ($sv -gt 0) { $f.Add("SERVICE_INSTALLED"); $red++; $b++ }
    }

    # ---- WMI event-subscription binding — persistence mechanism ----
    if ($hasWmi) {
        $wm = try { [int]$row.WmiPersistenceHits } catch { 0 }
        if ($wm -gt 0) { $f.Add("WMI_PERSISTENCE"); $red++; $b++; $loud = $true }
    }

    # ---- startup-folder LNK created by the candidate — autostart intent ----
    if ($hasStartup) {
        $su = try { [int]$row.StartupFilesCreated } catch { 0 }
        if ($su -gt 0) { $f.Add("STARTUP_LNK"); $red++; $b++; $loud = $true }
    }

    # ---- elevation: this app ran with a High/System integrity token ----
    if ($row.ProcessIntegrityLevel -eq "High" -or $row.ProcessIntegrityLevel -eq "System") {
        $f.Add("ELEVATED"); $red++; $b++
    }

    # ---- raw-IP callbacks: DNS-less outbound connections (C2-ish pattern) ----
    if ($hasRawIp) {
        $ri = try { [int]$row.RawIpConnections } catch { 0 }
        if ($ri -gt 0) { $f.Add("RAW_IP_CALLBACKS"); $red++; $b++ }
    }

    # ---- Defender AV verdicts (incl. PUA) — the gray-tool layer ----
    if ($hasAv) {
        $av = try { [int]$row.AvDetections } catch { 0 }
        if ($av -gt 0) { $f.Add("AV_FLAGGED"); $red++; $t++ }
    }

    # ---- sensitive-file reads (ssh keys, mail archives) — credential access ----
    if ($hasSensRead) {
        $sr = try { [int]$row.SensitiveFileReads } catch { 0 }
        if ($sr -gt 0) { $f.Add("SENSITIVE_READ"); $red++; $b++; $loud = $true }
    }

    # ---- process-tampering APIs (injection primitives) ----
    if ($hasTamper) {
        $pt = try { [int]$row.ProcessTamperingHits } catch { 0 }
        if ($pt -gt 0) { $f.Add("TAMPERING_APIS"); $red++; $b++ }
    }

    # ---- timestamp stomping (T1070.006) — flag-only note ----
    if ($hasTimes) {
        $ts = try { [int]$row.TimestampStomps } catch { 0 }
        if ($ts -gt 0) { $f.Add("TIMESTOMP") }
    }

    # ---- self-deletion (T1070.004): deleted a file with its own name ----
    if ($hasSelfDel) {
        $sd = try { [int]$row.SelfDeletes } catch { 0 }
        if ($sd -gt 0) { $f.Add("SELF_DELETED"); $red++; $b++; $loud = $true }
    }

    # ---- LNK creation by the candidate (non-installer creating shortcuts) ----
    if ($hasLnk) {
        $lk = try { [int]$row.ShellLinksCreated } catch { 0 }
        if ($lk -gt 0) { $f.Add("SHELL_LINK_CREATION") }
    }

    # ---- DPAPI access (T1555.004): decrypted DPAPI-protected secrets ----
    if ($hasDpapi) {
        $dp = try { [int]$row.DpapiAccesses } catch { 0 }
        if ($dp -gt 0) { $f.Add("DPAPI_ACCESS"); $red++; $b++; $loud = $true }
    }

    # ---- kernel driver loaded by the candidate (kernel-level code from an
    # unmanaged app — BYOVD/rootkit-flavored; Splunk's driver-load analytic
    # validates the signal). Red, NOT loud: legit VPN/hypervisor-style tools
    # load drivers too, and a signed+prevalent one should stay Stable. ----
    if ($hasDriverLoad) {
        $dl = try { [int]$row.DriverLoads } catch { 0 }
        if ($dl -gt 0) { $f.Add("DRIVER_LOADED"); $red++; $b++ }
    }

    # ---- Defender tampering (T1562.001): candidate tried to change Defender
    # XDR settings — Defender's own tampering event; a portable app attacking
    # Defender is a top-tier finding, so this is LOUD. ----
    if ($hasDefenderTamper) {
        $dt = try { [int]$row.DefenderTamperHits } catch { 0 }
        if ($dt -gt 0) { $f.Add("DEFENDER_TAMPERING"); $red++; $b++; $loud = $true }
    }

    # ---- SmartScreen: user clicked through a warning = deliberate ----
    if ($hasSmartScreen -and $row.SmartScreenVerdict -eq "UserOverride") {
        $f.Add("USER_OVERRIDE"); $red++; $t++
    }

    # ---- Defender alerts: this file triggered security alerts ----
    if ($hasAlerts -and $row.DefenderAlerts) {
        $ac = try { [int]$row.DefenderAlerts } catch { 0 }
        if (($row.IsMalwareAlert -eq "True") -or ($ac -gt 0)) { $f.Add("ALERT_HIT"); $red++; $b++; $loud = $true }
    }

    # ---- renamed binary (T1036.003): PE OriginalFileName vs actual FileName ----
    if ($row.OriginalFileName -and $row.FileName) {
        $orig = $row.OriginalFileName.ToLower().Trim()
        $actual = $row.FileName.ToLower().Trim()
        if ($orig -ne $actual) {
            if ($lolbins -contains $orig) { $f.Add("RENAMED_LOLBIN:$orig"); $red++; $b++; $loud = $true }
            else { $f.Add("RENAMED:$orig") }
        }
    }
    # ---- system-binary NAME in a user path (masquerade, T1036.003) ----
    # RENAMED only fires when OriginalFileName differs; a COPIED system binary
    # keeps its name — the name-in-user-path IS the signal here.
    if ($row.FileName) {
        if ($systemBinaries -contains $row.FileName.ToLower().Trim()) {
            $f.Add("SYSTEM_NAMED"); $red++; $b++; $loud = $true
        }
    }
    # ---- double extension lure (T1036.001): invoice.pdf.exe ----
    # catches spoofed OriginalFileName that defeats RENAMED; flag-only note
    if ($row.FileName -and $row.FileName.ToLower() -match '^.+\.(docx?|xlsx?|pptx?|pdf|jpg|jpeg|png|gif|zip|rar|7z|txt|mp3|mp4|iso|lnk|scr|bat|cmd|vbs|js)\.exe$') {
        $f.Add("DOUBLE_EXTENSION")
    }

    # ---- command-line patterns (ExampleCommandLine) ----
    if ($hasCommandLine -and $row.ExampleCommandLine) {
        $cl = $row.ExampleCommandLine.ToLower()
        if ($cl -match 'certutil.*(-urlcache|-decode)|bitsadmin.*/transfer|invoke-webrequest|iwr |invoke-expression|iex |start-bitstransfer') {
            $f.Add("DOWNLOAD_CRADLE"); $red++; $b++; $loud = $true
        }
        if ($cl -match '-enc(odedcommand)?\s|frombase64string|base64.*decode') {
            $f.Add("ENCODED_CMD"); $red++; $b++; $loud = $true
        }
        if ($cl -match 'rundll32|mshta|regsvr32.*/s|msbuild.*\.xml') { $f.Add("LOLBIN_INVOKE") }
    }

    # ---- persistence: portable app that established persistence ----
    if ($row.PersistenceDetected -eq "True") { $f.Add("PERSISTENCE"); $red++; $b++; $loud = $true }

    # ---- metadata spoofing (T1036.001): claims MS/Google/Adobe, unsigned ----
    if ($row.CompanyName -and ($hasCertCols -or $hasFileProfile)) {
        $cn = $row.CompanyName.ToLower().Trim()
        $isActuallySigned = $signed -or ($row.IsCertificateValid -eq "True")
        if ($spoofableVendors -contains $cn -and -not $isActuallySigned) {
            $f.Add("SPOOFED_METADATA"); $red++; $t++
        }
    }

    # ---- creation origin (InitiatorClass facts) ----
    if ($row.ExampleInitiatorClass -eq "OfficeMacro") { $f.Add("OFFICE_DROP") }
    if ($row.ExampleInitiatorClass -eq "ChatApp")     { $f.Add("CHAT_DROP") }
    if ($row.ExampleInitiatorClass -eq "CloudSync")   { $f.Add("CLOUD_SYNCED") }
    if ($row.ExampleInitiatorClass -eq "DownloadManager") { $f.Add("DM_DROP") }
    if ($row.ExampleInitiatorClass -eq "Torrent")     { $f.Add("TORRENT_DROP") }

    # ---- DLL sideloading: unsigned DLLs in the app's own folder ----
    # flag-only: shipping unsigned DLLs IS the portable packaging pattern (7-Zip)
    if ($row.SideloadedUnsignedDlls) { $f.Add("SIDELOAD_DLL"); $red++; $b++ }
    # search-order hijack shims: a SYSTEM-named DLL in the candidate's folder
    # (version.dll / winmm.dll / ws2_32.dll etc) = T1574.001 preloading trick
    if ($row.SideloadedUnsignedDlls) {
        foreach ($dll in ($row.SideloadedUnsignedDlls -split ";")) {
            if ($hijackDlls -contains $dll.Trim().ToLower()) {
                $f.Add("SEARCH_ORDER_HIJACK"); $red++; $b++
                break
            }
        }
    }

    # ---- categories ----
    if ($row.IsInstaller -eq "True")    { $f.Add("INSTALLER") }
    if ($isInternal)                    { $f.Add("INTERNAL_TOOL") }
    if ($row.IsAITool -eq "True")       { $f.Add("AI_TOOL") }
    if ($row.NonStandardPorts -eq "True") { $f.Add("NONSTD_PORT"); $red++; $b++ }
    if (-not $row.CompanyName -or -not $row.CompanyName.Trim()) { $f.Add("NO_METADATA") }

    # ---- recency (governance fact) ----
    if ($row.FirstSeenAny) {
        $fs = try { [datetime]$row.FirstSeenAny } catch { $null }
        if ($fs -and $fs -gt (Get-Date).AddDays(-30)) { $f.Add("NEW_APP") }
    }

    # ---- "looks fine, isn't governed": signed + prevalent + nothing else ----
    if ($signed -and $red -eq 0 -and $hasFileProfile) {
        $gp = try { [int64]$row.GlobalPrevalence } catch { 0 }
        if ($gp -ge 10000) { $f.Add("SIGNED_PREVALENT") }
    }

    return @{ Flags = ($f -join " "); Red = $red; T = $t; B = $b; C = $c; Loud = $loud }
}

# =============================================================================
# 3. PROCESS EVERYTHING
# =============================================================================
$results = [System.Collections.Generic.List[object]]::new()
$counter = 0; $total = $data.Count

foreach ($row in $data) {
    $counter++
    if ($counter % 1000 -eq 0) { Write-Host "  Processing $counter/$total" }

    $fl = Get-Flags $row
    $flags = $fl.Flags
    $red = $fl.Red
    $families = "T$($fl.T) B$($fl.B) C$($fl.C)"   # partition of Red — sums to it
    $loudSignal = if ($fl.Loud) { "True" } else { "False" }

    # Compact status profile: Trust · Prevalence · Age — categorical facts,
    # thresholds visible below (no hidden weights). "?" = signal unavailable.
    $profileTrust = if (-not $hasCertCols) { "?" }
                    elseif ($row.IsSigned -eq "True") {
                        if ($row.IsTrusted -eq "True" -or $row.IsTrusted -eq "Mixed") { "Signed" } else { "Untrusted" }
                    } else { "Unsigned" }
    $profilePrev = "?"
    if ($hasFileProfile -and $row.ProfileAvailability -eq "Available") {
        $gpv = try { [int64]$row.GlobalPrevalence } catch { 0 }
        $profilePrev = if ($gpv -lt 1000) { "Rare" } elseif ($gpv -lt 100000) { "Common" } else { "Prevalent" }
    }
    $profileAge = "?"
    if ($row.FirstSeenAny) {
        $fs = try { [datetime]$row.FirstSeenAny } catch { $null }
        if ($fs) { $profileAge = if ($fs -gt (Get-Date).AddDays(-30)) { "New" } else { "Established" } }
    }
    $profile = "$profileTrust | $profilePrev | $profileAge"   # ASCII separators — PS 5.1 misreads UTF-8 no-BOM sources

    # Launcher breakdown for display (facts from KQL counts)
    $launcherBreakdown = ""
    if ($hasLaunchers) {
        $launcherBreakdown = "User $($row.ExplorerLaunches) / Script $($row.ScriptLaunches) / System $($row.SystemLaunches) / Installer $($row.InstallerLaunches)"
    }

    $hashKey = $row.$hashCol

    # Growth trend (governance KPI): compare against previous run
    $growth = ""
    if ($prevDevices.Count -gt 0 -and $hashKey) {
        if ($prevDevices.ContainsKey($hashKey)) {
            $curDev = try { [int]$row.DeviceCount } catch { 0 }
            $prevDev = $prevDevices[$hashKey].Devices
            if ($curDev -gt $prevDev * 1.5 -and $curDev -gt $prevDev + 2) { $growth = "Growing" }
            elseif ($curDev -lt $prevDev * 0.5) { $growth = "Declining" }
            else { $growth = "Stable" }
        } else {
            $growth = "New"
        }
    }

    # Decision carry-over: vet once, track state (analyst fills this column)
    $decision = ""
    if ($hashKey -and $prevDecisions.ContainsKey($hashKey)) { $decision = $prevDecisions[$hashKey] }

    # Bucket — precedence: Loud > RedFlagged > Internal > New > Installer > Stable
    $isInternal = ($row.IsInternalTool -eq "True")
    $isInstaller = ($row.IsInstaller -eq "True")
    if ($fl.Loud)                         { $bucket = "Loud" }
    elseif ($red -ge 2 -and -not $isInternal) { $bucket = "RedFlagged" }
    elseif ($isInternal)                  { $bucket = "Internal" }
    elseif ($growth -eq "New")            { $bucket = "New" }
    elseif ($isInstaller)                 { $bucket = "Installer" }
    else                                  { $bucket = "Stable" }

    $results.Add([PSCustomObject]@{
        Bucket = $bucket
        RedFlagCount = $red
        Profile = $profile
        Families = $families
        LoudSignal = $loudSignal
        SHA1=if($columns -contains "SHA1"){$row.SHA1}else{""}
        SHA256=if($columns -contains "SHA256"){$row.SHA256}else{""}
        FileName=$row.FileName
        FolderPath=if($columns -contains "TopFolderPath"){$row.TopFolderPath}else{$row.FolderPath}
        PathCategory=if($hasPathCategory){$row.PathCategory}else{""}
        LauncherBreakdown=$launcherBreakdown
        DeviceCount=$row.DeviceCount
        UserCount=$row.UserCount
        DistinctDays=$row.DistinctDays
        ExecutionCount=$row.ExecutionCount
        GlobalPrevalence=if($hasFileProfile){$row.GlobalPrevalence}else{""}
        ThreatName=if($hasFileProfile){$row.ThreatName}else{""}
        IsCertificateValid=if($hasFileProfile){$row.IsCertificateValid}else{""}
        Signer=if($hasFileProfile -or $hasCertCols){$row.Signer}else{""}
        IsSigned=if($hasCertCols){$row.IsSigned}else{""}
        IsTrusted=if($hasCertCols){$row.IsTrusted}else{""}
        FileOriginUrl=if($hasOriginUrl){if($row.ExampleOriginUrl){$row.ExampleOriginUrl}else{$row.FileOriginUrl}}else{""}
        Initiator=if($hasInitiator){if($row.ExampleInitiator){$row.ExampleInitiator}else{$row.InitiatingProcessFileName_Create}}else{""}
        InitiatorClass=if($columns -contains "ExampleInitiatorClass"){$row.ExampleInitiatorClass}else{""}
        ProcessIntegrityLevel=if($hasIntegrityLevel){$row.ProcessIntegrityLevel}else{""}
        InTvmInventory=if($hasTvmVisible){$row.InTvmInventory}else{""}
        SmartScreenVerdict=if($hasSmartScreen){$row.SmartScreenVerdict}else{""}
        DefenderAlerts=if($hasAlerts){$row.DefenderAlerts}else{""}
        IsMalwareAlert=if($hasAlerts){$row.IsMalwareAlert}else{""}
        NetworkConnections=if($hasNetwork){$row.NetworkConnections}else{""}
        TopDestUrls=if($hasNetwork){$row.TopDestUrls}else{""}
        ParentProcess=if($hasParentChain){$row.ParentProcess}else{""}
        ExampleCommandLine=if($hasCommandLine){$row.ExampleCommandLine}else{""}
        OriginalFileName=if($columns -contains "OriginalFileName"){$row.OriginalFileName}else{""}
        PersistenceDetected=if($columns -contains "PersistenceDetected"){$row.PersistenceDetected}else{""}
        IsAITool=if($columns -contains "IsAITool"){$row.IsAITool}else{""}
        NonStandardPorts=if($columns -contains "NonStandardPorts"){$row.NonStandardPorts}else{""}
        SideloadedUnsignedDlls=if($columns -contains "SideloadedUnsignedDlls"){$row.SideloadedUnsignedDlls}else{""}
        IsInstaller=if($hasInstallerCol){$row.IsInstaller}else{""}
        IsInternalTool=if($hasInternalCol){$row.IsInternalTool}else{""}
        FilesCreated=if($hasFilesCreated){$row.FilesCreated}else{""}
        AsrUntrustedHits=if($hasAsr){$row.AsrUntrustedHits}else{""}
        InTvmFileEvidence=if($hasTvmEv){$row.InTvmFileEvidence}else{""}
        IsRmmTool=if($hasRmm){$row.IsRmmTool}else{""}
        RemoteLaunchHits=if($hasRemoteLaunch){$row.RemoteLaunchHits}else{""}
        ServicesInstalled=if($hasSvcs){$row.ServicesInstalled}else{""}
        WmiPersistenceHits=if($hasWmi){$row.WmiPersistenceHits}else{""}
        StartupFilesCreated=if($hasStartup){$row.StartupFilesCreated}else{""}
        RawIpConnections=if($hasRawIp){$row.RawIpConnections}else{""}
        AvDetections=if($hasAv){$row.AvDetections}else{""}
        SensitiveFileReads=if($hasSensRead){$row.SensitiveFileReads}else{""}
        ProcessTamperingHits=if($hasTamper){$row.ProcessTamperingHits}else{""}
        TimestampStomps=if($hasTimes){$row.TimestampStomps}else{""}
        SelfDeletes=if($hasSelfDel){$row.SelfDeletes}else{""}
        ShellLinksCreated=if($hasLnk){$row.ShellLinksCreated}else{""}
        DpapiAccesses=if($hasDpapi){$row.DpapiAccesses}else{""}
        DriverLoads=if($hasDriverLoad){$row.DriverLoads}else{""}
        DefenderTamperHits=if($hasDefenderTamper){$row.DefenderTamperHits}else{""}
        VersionCount=if($columns -contains "VersionCount"){$row.VersionCount}else{""}
        BundleMembers=if($columns -contains "BundleMembers"){$row.BundleMembers}else{""}
        FirstSeenAny=if($columns -contains "FirstSeenAny"){$row.FirstSeenAny}else{""}
        Departments=if($columns -contains "Departments"){$row.Departments}else{""}
        UsersSample=if($columns -contains "UsersSample"){$row.UsersSample}else{""}
        IsUnknown=if($columns -contains "IsUnknown"){$row.IsUnknown}else{""}
        Confidence=if($columns -contains "Confidence"){$row.Confidence}else{""}
        Growth=$growth
        Decision=$decision
        Flags=$flags
    })
}

# =============================================================================
# 4. OUTPUT
# =============================================================================
Write-Host ""
Write-Host "=== Results ===" -ForegroundColor Cyan

$byBucket = $results | Group-Object Bucket | Sort-Object Count -Descending
foreach ($g in $byBucket) { Write-Host ("{0,-16} {1}" -f $g.Name, $g.Count) }

Write-Host ""
Write-Host "Top review candidates (RedFlagCount desc):" -ForegroundColor Yellow
$results | Sort-Object @{Expression="LoudSignal";Descending=$true}, @{Expression="RedFlagCount";Descending=$true}, @{Expression="DeviceCount";Descending=$true} | Select-Object -First 15 `
    @{N="RF";E={$_.RedFlagCount}}, FileName, Profile, @{N="T/B/C";E={$_.Families}}, DeviceCount, DistinctDays, Growth, Flags |
    Format-Table -AutoSize -Wrap

$results | Export-Csv $OutputCsv -NoTypeInformation -Encoding UTF8
Write-Host "[SAVE] $OutputCsv (all results, one file)" -ForegroundColor Green

$outBase = [System.IO.Path]::GetFileNameWithoutExtension($OutputCsv)
$outDir  = if ([System.IO.Path]::GetDirectoryName($OutputCsv)) { [System.IO.Path]::GetDirectoryName($OutputCsv) } else { "." }
$redCsv = Join-Path $outDir ($outBase + "-redflagged.csv")
$results | Where-Object { $_.Bucket -eq "Loud" -or $_.Bucket -eq "RedFlagged" } | Export-Csv $redCsv -NoTypeInformation -Encoding UTF8
Write-Host "[SAVE] $redCsv (review list: Loud + RedFlagged)" -ForegroundColor Green

Write-Host ""
Write-Host "Done." -ForegroundColor Cyan
