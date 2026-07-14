$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot

$Python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Creating the virtual environment..."
    python -m venv .venv
}

Write-Host "Installing build requirements..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt
& $Python -m pip install pyinstaller

Write-Host "Removing previous build output..."
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Write-Host "Building Housing Search Assistant..."
& $Python -m PyInstaller --clean --noconfirm HousingSearchAssistant.spec

$Exe = Join-Path $PSScriptRoot "dist\HousingSearchAssistant\HousingSearchAssistant.exe"

if (-not (Test-Path $Exe)) {
    throw "The build finished without creating the expected executable."
}

Write-Host ""
Write-Host "BUILD COMPLETE"
Write-Host "Executable:"
Write-Host $Exe
Write-Host ""
Write-Host "Keep the entire dist\HousingSearchAssistant folder together."
Write-Host "Double-click HousingSearchAssistant.exe inside that folder."
