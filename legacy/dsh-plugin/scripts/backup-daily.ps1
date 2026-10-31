# Daily SQLite backup for mnemosyne.
# Usage:
#   pwsh scripts/backup-daily.ps1
#   pwsh scripts/backup-daily.ps1 -DataDir "D:\data\mnemosyne"
param(
  [string]$DataDir = "",
  [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Service = Join-Path $Root "service"
if (-not (Test-Path (Join-Path $Service "src\mnemosyne\main.py"))) {
  throw "service/ missing next to plugin root: $Service"
}

$py = if ($Python) { $Python } elseif ($env:DSH_MEMORY_PYTHON) { $env:DSH_MEMORY_PYTHON } else { "python" }
$env:PYTHONPATH = (Join-Path $Service "src") + [IO.Path]::PathSeparator + ($env:PYTHONPATH)

$args = @("-m", "mnemosyne.cli", "backup")
if ($DataDir) { $args += @("--data-dir", $DataDir) }

& $py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
