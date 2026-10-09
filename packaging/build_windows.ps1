[CmdletBinding()]
param(
    [string]$Python = "python",
    [string]$Npm = "npm"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

function Invoke-Checked {
    param([scriptblock]$Command, [string]$Step)
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Step misslyckades med felkod $LASTEXITCODE."
    }
}

Push-Location $projectRoot
try {
    Invoke-Checked { & $Npm --prefix frontend ci } "npm ci"
    Invoke-Checked { & $Npm --prefix frontend run build } "Frontendbyggning"
    Invoke-Checked { & $Python -m pip install . pyinstaller } "Pythonberoenden"
    Invoke-Checked { & $Python -m PyInstaller --noconfirm --clean --onedir --name Tentaoptimering `
        --paths src `
        --add-data "config;config" `
        --add-data "frontend\dist;frontend\dist" `
        --collect-all ortools `
        --collect-all pandas `
        --collect-all openpyxl `
        --collect-all fastapi `
        --collect-all uvicorn `
        packaging\desktop_entry.py } "PyInstaller"
    Write-Host "Färdig distribution: $projectRoot\dist\Tentaoptimering\Tentaoptimering.exe"
}
finally {
    Pop-Location
}
