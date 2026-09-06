param(
    [switch]$Watch
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceDir = Join-Path $repoRoot "Output"
$envFile = Join-Path $repoRoot ".env"
$logDir = Join-Path $env:LOCALAPPDATA "Meka RPA\logs"
$logFile = Join-Path $logDir "mega_sync.log"

function Write-SyncLog {
    param([string]$Message)
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    Add-Content -LiteralPath $logFile -Encoding UTF8 -Value (
        "{0:yyyy-MM-dd HH:mm:ss} | {1}" -f (Get-Date), $Message
    )
}

function Get-DotEnvValue {
    param([string]$Name)
    if (-not (Test-Path -LiteralPath $envFile)) {
        return $null
    }
    $prefix = "$Name="
    $line = Get-Content -LiteralPath $envFile | Where-Object {
        $_.TrimStart().StartsWith($prefix)
    } | Select-Object -Last 1
    if (-not $line) {
        return $null
    }
    $value = $line.Substring($line.IndexOf("=") + 1).Trim().Trim('"').Trim("'")
    return [Environment]::ExpandEnvironmentVariables($value)
}

$destinationDir = Get-DotEnvValue "MEGA_OUTPUT_DIR"
if (-not $destinationDir) {
    throw "MEGA_OUTPUT_DIR nao configurado no arquivo .env."
}
if (-not (Test-Path -LiteralPath $sourceDir)) {
    throw "Diretorio Output nao encontrado: $sourceDir"
}

function Sync-Output {
    New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
    & robocopy $sourceDir $destinationDir /MIR /R:5 /W:2 /NFL /NDL /NJH /NJS /NP | Out-Null
    $robocopyExit = $LASTEXITCODE
    if ($robocopyExit -gt 7) {
        throw "Falha no robocopy. Codigo: $robocopyExit"
    }
    Write-SyncLog "Output sincronizado com '$destinationDir'. Codigo robocopy: $robocopyExit"
}

Sync-Output
if (-not $Watch) {
    exit 0
}

$watcher = [System.IO.FileSystemWatcher]::new($sourceDir, "*")
$watcher.IncludeSubdirectories = $true
$watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName, DirectoryName, LastWrite, Size'

$eventIds = @(
    "MekaRPA.Output.Changed",
    "MekaRPA.Output.Created",
    "MekaRPA.Output.Deleted",
    "MekaRPA.Output.Renamed"
)

try {
    Register-ObjectEvent $watcher Changed -SourceIdentifier $eventIds[0] | Out-Null
    Register-ObjectEvent $watcher Created -SourceIdentifier $eventIds[1] | Out-Null
    Register-ObjectEvent $watcher Deleted -SourceIdentifier $eventIds[2] | Out-Null
    Register-ObjectEvent $watcher Renamed -SourceIdentifier $eventIds[3] | Out-Null
    $watcher.EnableRaisingEvents = $true
    Write-SyncLog "Monitor iniciado para '$sourceDir'."

    while ($true) {
        $event = Wait-Event -Timeout 5
        if ($null -eq $event) {
            continue
        }
        Get-Event | Remove-Event -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 3
        try {
            Sync-Output
        }
        catch {
            Write-SyncLog "ERRO: $($_.Exception.Message)"
        }
    }
}
finally {
    $watcher.EnableRaisingEvents = $false
    foreach ($eventId in $eventIds) {
        Unregister-Event -SourceIdentifier $eventId -ErrorAction SilentlyContinue
    }
    $watcher.Dispose()
    Write-SyncLog "Monitor encerrado."
}
