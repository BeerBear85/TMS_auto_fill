# TMS Auto Fill - Initial Setup Script
# This script sets up the development environment for the Timesheet Bot

Write-Host "================================" -ForegroundColor Cyan
Write-Host "TMS Timesheet Bot - Initial Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
Write-Host "[1/4] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Found: $pythonVersion" -ForegroundColor Green

        # Check Python version is 3.8 or higher
        $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
        if ($versionMatch) {
            $majorVersion = [int]$Matches[1]
            $minorVersion = [int]$Matches[2]

            if (($majorVersion -lt 3) -or ($majorVersion -eq 3 -and $minorVersion -lt 8)) {
                Write-Host "  ✗ Error: Python 3.8 or higher is required" -ForegroundColor Red
                Write-Host "  Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
                exit 1
            }
        }
    }
} catch {
    Write-Host "  ✗ Error: Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "  Please install Python 3.8+ from https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "[2/4] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  ! Virtual environment already exists. Skipping creation." -ForegroundColor Yellow
} else {
    python -m venv venv
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Virtual environment created successfully" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Error: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment and install dependencies
Write-Host ""
Write-Host "[3/4] Installing Python dependencies..." -ForegroundColor Yellow
Write-Host "  Activating virtual environment..." -ForegroundColor Gray

# Run pip install in the virtual environment
& "venv\Scripts\python.exe" -m pip install --upgrade pip | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Error: Failed to upgrade pip" -ForegroundColor Red
    exit 1
}

& "venv\Scripts\pip.exe" install -e .
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Package and dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "  ✗ Error: Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Install Playwright browsers
Write-Host ""
Write-Host "[4/4] Installing Playwright browsers..." -ForegroundColor Yellow
Write-Host "  This may take a few minutes..." -ForegroundColor Gray
& "venv\Scripts\playwright.exe" install chromium
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Chromium browser installed successfully" -ForegroundColor Green
} else {
    Write-Host "  ✗ Error: Failed to install Playwright browsers" -ForegroundColor Red
    exit 1
}

# Success message
Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host "✓ Setup completed successfully!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Activate the virtual environment:" -ForegroundColor White
Write-Host "     venv\Scripts\activate" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Generate a CSV template from TMS:" -ForegroundColor White
Write-Host "     python -m timesheet_bot fetch_input_csv" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Or launch the GUI:" -ForegroundColor White
Write-Host "     python -m timesheet_bot.gui" -ForegroundColor Gray
Write-Host ""
Write-Host "For more information, see README.md" -ForegroundColor Cyan
Write-Host ""
