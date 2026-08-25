# Windows 11 Privacy Hardening Script
# Run as Administrator in PowerShell
# Verified against Microsoft Docs and ntdevlabs/nano11 (July 2026)

Write-Output "=== Disabling Advertising ID ==="
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo" -Name "Enabled" -Value 0 -Force

Write-Output "=== Disabling Tailored Experiences ==="
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy" -Name "TailoredExperiencesWithDiagnosticDataEnabled" -Value 0 -Force

Write-Output "=== Restricting Ink & Text Collection ==="
Set-ItemProperty -Path "HKCU:\Software\Microsoft\InputPersonalization" -Name "RestrictImplicitInkCollection" -Value 1 -Force
Set-ItemProperty -Path "HKCU:\Software\Microsoft\InputPersonalization" -Name "RestrictImplicitTextCollection" -Value 1 -Force

Write-Output "=== Disabling Contact Harvesting ==="
Set-ItemProperty -Path "HKCU:\Software\Microsoft\InputPersonalization\TrainedDataStore" -Name "HarvestContacts" -Value 0 -Force

Write-Output "=== Disabling Content Delivery Manager (ads, silent installs, tips) ==="
$cdmPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"
Set-ItemProperty -Path $cdmPath -Name "SilentInstalledAppsEnabled" -Value 0 -Force
Set-ItemProperty -Path $cdmPath -Name "SoftLandingEnabled" -Value 0 -Force
Set-ItemProperty -Path $cdmPath -Name "OemPreInstalledAppsEnabled" -Value 0 -Force
Set-ItemProperty -Path $cdmPath -Name "SystemPaneSuggestionsEnabled" -Value 0 -Force

Write-Output "=== Disabling Online Speech Recognition ==="
New-Item -Path "HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy" -Force -ErrorAction SilentlyContinue | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy" -Name "HasAccepted" -Value 0 -Force

Write-Output "=== Disabling Copilot ==="
New-Item -Path "HKCU:\Software\Policies\Microsoft\Windows\WindowsCopilot" -Force -ErrorAction SilentlyContinue | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Policies\Microsoft\Windows\WindowsCopilot" -Name "TurnOffWindowsCopilot" -Value 1 -Force

Write-Output "=== Setting Telemetry to Minimum ==="
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry" -Value 0 -Force
Set-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection" -Name "AllowTelemetry" -Value 0 -Force

Write-Output "=== Disabling Activity History ==="
$sysPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\System"
Set-ItemProperty -Path $sysPath -Name "EnableActivityFeed" -Value 0 -Force
Set-ItemProperty -Path $sysPath -Name "PublishUserActivities" -Value 0 -Force
Set-ItemProperty -Path $sysPath -Name "UploadUserActivities" -Value 0 -Force

Write-Output "=== Disabling Windows Consumer Features (Store suggestions) ==="
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent" -Force -ErrorAction SilentlyContinue | Out-Null
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent" -Name "DisableWindowsConsumerFeatures" -Value 1 -Force

Write-Output ""
Write-Output "=== Done. Some changes require a restart to take effect. ==="
Write-Output "NOTE: AllowTelemetry=0 on Pro edition caps at Basic (1). Only Enterprise gets Security level."
Write-OUTPUT "NOTE: GDID cannot be disabled via registry. Block telemetry domains at DNS level instead."
