$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
py -m pip install -r requirements-dev.txt
$iconArgs = @()
if (Test-Path "assets\AutoPomodoro.ico") {
    $iconArgs = @("--icon", "assets\AutoPomodoro.ico")
}
py -m PyInstaller --noconfirm --clean --windowed --name "AutoPomodoro" --add-data "assets/app-icon.svg:assets" @iconArgs main.py

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
    & $iscc "windows-installer.iss"
    Write-Host "Installer complete: dist\AutoPomodoro-Official-1.0-Windows-Setup.exe"
} else {
    Write-Warning "Inno Setup 6 was not found. The portable app is ready, but the installer was not generated."
}
Write-Host "Portable app: dist\AutoPomodoro\AutoPomodoro.exe"
