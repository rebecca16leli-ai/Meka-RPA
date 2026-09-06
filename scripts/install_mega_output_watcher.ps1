param(
    [string]$TaskName = "Meka RPA - Sincronizar Output com MEGA"
)

$ErrorActionPreference = "Stop"
$watcherScript = Join-Path $PSScriptRoot "sync_output_to_mega.ps1"
if (-not (Test-Path -LiteralPath $watcherScript)) {
    throw "Script de sincronizacao nao encontrado: $watcherScript"
}

$user = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$watcherScript`" -Watch"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arguments
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $user
$principal = New-ScheduledTaskPrincipal `
    -UserId $user `
    -LogonType Interactive `
    -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Sincroniza automaticamente o Output do Meka-RPA com a pasta local do MEGA." `
    -Force | Out-Null

Start-ScheduledTask -TaskName $TaskName
Write-Output "Monitor instalado e iniciado: $TaskName"
