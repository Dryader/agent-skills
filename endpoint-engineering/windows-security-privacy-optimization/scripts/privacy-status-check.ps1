# Windows 11 Privacy Status Checker
# Run in PowerShell — checks current state of privacy-relevant registry keys
# Outputs each setting as "Name = Value" for easy scanning

$checks = @(
    @{N="Advertising ID"; P="HKCU:\Software\Microsoft\Windows\CurrentVersion\AdvertisingInfo"; K="Enabled"},
    @{N="Tailored Experiences"; P="HKCU:\Software\Microsoft\Windows\CurrentVersion\Privacy"; K="TailoredExperiencesWithDiagnosticDataEnabled"},
    @{N="Restrict Implicit Ink"; P="HKCU:\Software\Microsoft\InputPersonalization"; K="RestrictImplicitInkCollection"},
    @{N="Restrict Implicit Text"; P="HKCU:\Software\Microsoft\InputPersonalization"; K="RestrictImplicitTextCollection"},
    @{N="Harvest Contacts"; P="HKCU:\Software\Microsoft\InputPersonalization\TrainedDataStore"; K="HarvestContacts"},
    @{N="Start Suggestions"; P="HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; K="SystemPaneSuggestionsEnabled"},
    @{N="Silent App Install"; P="HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; K="SilentInstalledAppsEnabled"},
    @{N="SoftLanding"; P="HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; K="SoftLandingEnabled"},
    @{N="OEM PreInstalled Apps"; P="HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; K="OemPreInstalledAppsEnabled"},
    @{N="Rotating Lock Screen"; P="HKCU:\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager"; K="RotatingLockScreenEnabled"},
    @{N="Telemetry AllowTelemetry"; P="HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection"; K="AllowTelemetry"},
    @{N="Telemetry Policy"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection"; K="AllowTelemetry"},
    @{N="Copilot User"; P="HKCU:\Software\Policies\Microsoft\Windows\WindowsCopilot"; K="TurnOffWindowsCopilot"},
    @{N="Copilot Machine"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot"; K="TurnOffWindowsCopilot"},
    @{N="Activity Feed"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\System"; K="EnableActivityFeed"},
    @{N="Publish Activities"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\System"; K="PublishUserActivities"},
    @{N="Upload Activities"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\System"; K="UploadUserActivities"},
    @{N="Feedback SIUF"; P="HKCU:\Software\Microsoft\Siuf\Rules"; K="NumberOfSIUFInPeriod"},
    @{N="Online Speech"; P="HKCU:\Software\Microsoft\Speech_OneCore\Settings\OnlineSpeechPrivacy"; K="HasAccepted"},
    @{N="Consumer Features"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\CloudContent"; K="DisableWindowsConsumerFeatures"},
    @{N="Web Search"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search"; K="DisableWebSearch"},
    @{N="Cortana"; P="HKLM:\SOFTWARE\Policies\Microsoft\Windows\Windows Search"; K="AllowCortana"}
)

foreach ($c in $checks) {
    $result = "NOT SET"
    if (Test-Path $c.P) {
        $val = Get-ItemProperty -Path $c.P -Name $c.K -ErrorAction SilentlyContinue
        if ($val -ne $null) {
            $result = $val.($c.K)
        }
    }
    Write-Output "$($c.N) = $result"
}
