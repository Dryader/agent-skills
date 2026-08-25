# TPM / fTPM diagnostics probe. Run from WSL (non-elevated, read-only):
#   cp scripts/tpm-diagnostics.ps1 /mnt/c/Users/<user>/AppData/Local/Temp/
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\<user>\AppData\Local\Temp\tpm-diagnostics.ps1"
# Output is UTF-8 already - do NOT pipe through iconv -f UTF-16 (mojibake).
# Edit the "Context around a burst" times to match the Event 14 timestamps in question.
$ErrorActionPreference = 'SilentlyContinue'
function Section($t) { Write-Output ""; Write-Output ("==================== " + $t + " ====================") }

Section "Machine"
$cs = Get-CimInstance Win32_ComputerSystem
Write-Output ("ComputerName: " + $cs.Name)
$os = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
Write-Output ("Windows: " + $os.ProductName + " " + $os.DisplayVersion + " build " + $os.CurrentBuild + "." + $os.UBR)
$bios = Get-CimInstance Win32_BIOS
Write-Output ("BIOS: " + $bios.Manufacturer + " " + $bios.SMBIOSBIOSVersion + " released " + $bios.ReleaseDate.ToString('yyyy-MM-dd'))
$mb = Get-CimInstance Win32_BaseBoard
Write-Output ("Board: " + $mb.Manufacturer + " " + $mb.Product)
$cpu = Get-CimInstance Win32_Processor
Write-Output ("CPU: " + $cpu.Name)
Write-Output ("Last boot: " + (Get-CimInstance Win32_OperatingSystem).LastBootUpTime)

Section "TPM device status (PnP, non-admin OK)"
Get-PnpDevice -Class SecurityDevices | Select-Object Status,FriendlyName | Format-Table -AutoSize | Out-String -Width 200

Section "TPM via Get-Tpm (needs admin)"
try { Get-Tpm | Format-List TpmPresent,TpmReady,TpmEnabled,TpmActivated,OwnerAuthPresent,ManufacturerVersion,SpecVersion } catch { Write-Output ("Get-Tpm failed: " + $_.Exception.Message) }

Section "BitLocker (needs admin)"
try { Get-BitLockerVolume | Select-Object MountPoint,VolumeStatus,ProtectionStatus,EncryptionPercentage | Format-List } catch { Write-Output ("Get-BitLockerVolume failed: " + $_.Exception.Message) }

Section "TPM provider events - last 15"
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='TPM'} -MaxEvents 15 | ForEach-Object {
  $msg = $_.Message; if ($msg.Length -gt 150) { $msg = $msg.Substring(0,150) }
  Write-Output ($_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss') + "  ID " + $_.Id + "  " + $msg)
}

Section "TPM Event 14 count by day (last 30 days)"
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='TPM'; Id=14; StartTime=(Get-Date).AddDays(-30)} | Group-Object { $_.TimeCreated.ToString('yyyy-MM-dd') } | Sort-Object Name | ForEach-Object { Write-Output ($_.Name + " : " + $_.Count) }

Section "All TPM provider event IDs (last 30 days)"
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='TPM'; StartTime=(Get-Date).AddDays(-30)} | Group-Object Id | ForEach-Object { Write-Output ("EventID " + $_.Name + " : " + $_.Count) }

Section "Context around a burst - EDIT TIMES TO MATCH (all providers)"
Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=[datetime]'2026-08-12T19:44:00'; EndTime=[datetime]'2026-08-12T19:50:00'} | Select-Object TimeCreated,Id,ProviderName,LevelDisplayName | Format-Table -AutoSize | Out-String -Width 250

Section "Kernel-Power 41 (unexpected shutdown), last 30 days"
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=41; StartTime=(Get-Date).AddDays(-30)} | ForEach-Object { Write-Output ($_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss')) }

Section "Sleep (42) / resume (107) counts, last 30 days"
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-Kernel-Power'; Id=@(42,107); StartTime=(Get-Date).AddDays(-30)} | Group-Object Id | ForEach-Object { Write-Output ("EventID " + $_.Name + " : " + $_.Count) }

Section "WHEA hardware errors, last 30 days (0 = no CPU/RAM instability)"
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-WHEA-Logger'; StartTime=(Get-Date).AddDays(-30)} | Group-Object Id | ForEach-Object { Write-Output ("WHEA EventID " + $_.Name + " : " + $_.Count) }

Section "TPM-related event logs available"
Get-WinEvent -ListLog *TPM* | Select-Object LogName,RecordCount,IsEnabled | Format-Table -AutoSize | Out-String -Width 200

Section "Done"
