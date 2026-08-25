# Windows running-inventory script (16 sections). Verified working 2026-08 on Win11 Pro 25H2 (build 26200).
# Run from WSL:  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\path\to\win-inventory.ps1"
# Non-elevated is fine for most sections. Admin needed for: Confirm-SecureBootUEFI, Get-Tpm,
# driverquery Signed column (blank for ALL drivers when not elevated), netstat -b.
# Output is large (~130KB on a normal desktop) — redirect to a log and page it, don't rely on inline capture.
$ErrorActionPreference = 'Continue'
$W = 220

Write-Output "=== WINDOWS INVENTORY $(Get-Date -Format 'yyyy-MM-dd HH:mm') ==="
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$os = Get-CimInstance Win32_OperatingSystem
Write-Output ("Elevated: {0} | OS: {1} build {2}" -f $isAdmin, $os.Caption, $os.BuildNumber)

Write-Output ""
Write-Output "=== 1. TOP CPU PROCESSES ==="
Get-Process | Sort-Object CPU -Descending | Select-Object -First 12 Name, Id, @{n='CPU_s';e={[math]::Round($_.CPU,1)}}, @{n='MemMB';e={[math]::Round($_.WorkingSet64/1MB)}} | Format-Table -AutoSize | Out-String -Width $W

Write-Output "=== 2. THIRD-PARTY PROCESSES (executable outside C:\Windows) ==="
Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath -notlike 'C:\Windows\*' } | Select-Object Name, ProcessId, ParentProcessId, ExecutablePath | Sort-Object Name | Format-Table -AutoSize | Out-String -Width $W

Write-Output "=== 3. SYSTEM-NAMED PROCESSES WITH NON-STANDARD PATHS ==="
$sysprocs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(svchost|lsass|csrss|wininit|services|smss|spoolsv|winlogon|conhost|dwm|explorer|MsMpEng)\.exe$' -and $_.ExecutablePath -and $_.ExecutablePath -notlike 'C:\Windows\System32\*' -and $_.ExecutablePath -notlike 'C:\Windows\SysWOW64\*' }
if ($sysprocs) { $sysprocs | Select-Object Name, ProcessId, ParentProcessId, ExecutablePath | Format-Table -AutoSize | Out-String -Width $W } else { Write-Output "(clean)" }
# NOTE: explorer.exe at C:\WINDOWS\Explorer.EXE (root, not System32) is the legit location — case difference is NOT a flag.

Write-Output "=== 4. PROCESSES WITH NO PATH OR RUNNING FROM TEMP/APPDATA/DOWNLOADS ==="
$weird = Get-CimInstance Win32_Process | Where-Object { -not $_.ExecutablePath -or $_.ExecutablePath -match 'Temp|AppData|\\Downloads\\|\\Public\\' } | Select-Object Name, ProcessId, ParentProcessId, ExecutablePath, CommandLine
if ($weird) { $weird | Format-Table -AutoSize -Wrap | Out-String -Width $W } else { Write-Output "(none)" }
# NOTE: non-elevated runs show empty ExecutablePath for kernel/system processes — expected noise, not findings.
# AppData\Local\Discord etc. is the normal Electron install location, NOT a flag.

Write-Output "=== 5. STARTUP COMMANDS (Win32_StartupCommand) ==="
$su = Get-CimInstance Win32_StartupCommand
if ($su) { $su | Format-List Name, Command, Location, User | Out-String -Width $W } else { Write-Output "(none)" }

Write-Output "=== 6. RUN / RUNONCE KEYS ==="
foreach ($k in 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run','HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce') {
  Write-Output "KEY $k"
  if (Test-Path $k) {
    $vals = (Get-ItemProperty $k).PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' }
    if ($vals) { $vals | ForEach-Object { Write-Output ("  {0} = {1}" -f $_.Name, $_.Value) } } else { Write-Output "  (empty)" }
  } else { Write-Output "  (missing)" }
}

Write-Output ""
Write-Output "=== 7. SCHEDULED TASKS OUTSIDE \Microsoft (enabled) ==="
Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' -and $_.TaskPath -notlike '\Microsoft*' } | ForEach-Object {
  $act = ($_.Actions | ForEach-Object { $_.Execute }) -join '; '
  Write-Output ("{0}{1}  ->  {2}" -f $_.TaskPath, $_.TaskName, $act)
}

Write-Output ""
Write-Output "=== 8. TASKS UNDER \Microsoft\Windows RUNNING NON-WINDOWS EXECUTABLES ==="
Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' -and $_.TaskPath -like '\Microsoft\Windows\*' } | ForEach-Object {
  $acts = $_.Actions | Where-Object { $_.Execute -and $_.Execute -notlike 'C:\Windows\*' -and $_.Execute -notlike '%windir%*' -and $_.Execute -notlike 'ms-settings*' }
  if ($acts) { Write-Output ("{0}{1}  ->  {2}" -f $_.TaskPath, $_.TaskName, (($acts | ForEach-Object { $_.Execute }) -join '; ')) }
}
Write-Output "(done)"

Write-Output ""
Write-Output "=== 9. RUNNING SERVICES OUTSIDE C:\Windows ==="
Get-CimInstance Win32_Service | Where-Object { $_.State -eq 'Running' -and $_.PathName -notlike '*C:\Windows\*' } | Select-Object Name, DisplayName, PathName | Format-Table -AutoSize -Wrap | Out-String -Width $W

Write-Output "=== 10. KERNEL DRIVERS NOT SIGNED ==="
try {
  $drv = driverquery /v /fo csv | ConvertFrom-Csv
  Write-Output ("total drivers: {0}" -f $drv.Count)
  # NOTE: Signed column is BLANK for every driver when not elevated — inconclusive, re-run as admin.
  $bad = $drv | Where-Object { $_.Signed -ne 'True' }
  if ($bad) { $bad | Select-Object 'Module Name', 'Display Name', 'State', 'Signed' | Format-Table -AutoSize | Out-String -Width $W } else { Write-Output "(all signed)" }
} catch { Write-Output ("driverquery failed: {0}" -f $_.Exception.Message) }

Write-Output ""
Write-Output "=== 11. ESTABLISHED CONNECTIONS (non-local) ==="
try {
  $conns = Get-NetTCPConnection -State Established -ErrorAction Stop | Where-Object { $_.RemoteAddress -notin @('127.0.0.1','::1','0.0.0.0','::','[::1]') }
  if ($conns) {
    $conns | ForEach-Object {
      $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
      Write-Output ("{0,-22} (pid {1,-6})  {2}:{3} -> {4}:{5}" -f $p.ProcessName, $_.OwningProcess, $_.LocalAddress, $_.LocalPort, $_.RemoteAddress, $_.RemotePort)
    }
  } else { Write-Output "(none)" }
} catch { Write-Output ("netstat query failed: {0}" -f $_.Exception.Message) }

Write-Output ""
Write-Output "=== 12. LISTENING PORTS ==="
try {
  Get-NetTCPConnection -State Listen -ErrorAction Stop | ForEach-Object {
    $p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
    Write-Output ("{0}:{1} <- {2} (pid {3})" -f $_.LocalAddress, $_.LocalPort, $p.ProcessName, $_.OwningProcess)
  } | Sort-Object -Unique
} catch { Write-Output ("listener query failed: {0}" -f $_.Exception.Message) }

Write-Output ""
Write-Output "=== 13. WMI PERSISTENCE CONSUMERS ==="
try {
  $c = Get-WmiObject -Namespace root\subscription -Class __EventConsumer -ErrorAction Stop
  if ($c) { $c | Select-Object Name, CommandLineTemplate, ScriptText | Format-List | Out-String -Width $W } else { Write-Output "(none)" }
} catch { Write-Output "(query failed: $($_.Exception.Message))" }

Write-Output "=== 14. DEFENDER STATUS ==="
Get-MpComputerStatus | Select-Object AMRunningMode, RealTimeProtectionEnabled, AntivirusEnabled, AntivirusSignatureLastUpdated, AntivirusSignatureVersion, TamperProtectionSource | Format-List | Out-String -Width $W

Write-Output "=== 15. RECENT DEFENDER DETECTIONS ==="
try {
  $d = Get-MpThreatDetection -ErrorAction Stop | Sort-Object InitialDetectionTime -Descending | Select-Object -First 10
  if ($d) { $d | Select-Object InitialDetectionTime, ProcessName, Resources | Format-Table -AutoSize | Out-String -Width $W } else { Write-Output "(none)" }
} catch { Write-Output "(query failed: $($_.Exception.Message))" }

Write-Output "=== 16. BOOT / INTEGRITY STATUS ==="
try { Write-Output ("SecureBoot: {0}" -f (Confirm-SecureBootUEFI)) } catch { Write-Output ("SecureBoot: check failed ({0}) - needs admin" -f $_.Exception.Message) }
try { $t = Get-Tpm; Write-Output ("TPM ready: {0} | enabled: {1} | activated: {2}" -f $t.TpmReady, $t.TpmEnabled, $t.TpmActivated) } catch { Write-Output ("TPM: check failed ({0}) - needs admin" -f $_.Exception.Message) }
try {
  $av = (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\AvailableUpdates' -ErrorAction Stop).AvailableUpdates
  Write-Output ("Secure Boot cert migration remaining bits: {0} (0 = done)" -f $av)
} catch { Write-Output "Secure Boot cert migration: key not present (already consumed or N/A)" }
Write-Output "=== END ==="
