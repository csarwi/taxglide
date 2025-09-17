# Upload TaxGlide Release to GitHub
# This script uploads your locally built ZIP to GitHub releases
#
# Prerequisites:
# - GitHub CLI (gh) installed: https://cli.github.com/
# - Authenticated with GitHub: gh auth login
#
# Usage:
#   .\upload-release.ps1                    # Auto-detect version from pyproject.toml
#   .\upload-release.ps1 -Version 0.4.1    # Specify version
#   .\upload-release.ps1 -Version 0.4.1 -Notes "Bug fixes and new features"

param(
    [Parameter(Mandatory=$false)]
    [string]$Version,
    
    [Parameter(Mandatory=$false)]
    [string]$Notes = "Latest TaxGlide release with new features and improvements."
)

# Function to extract version from pyproject.toml
function Get-ProjectVersion {
    param([string]$TomlPath = "pyproject.toml")
    if (-not (Test-Path $TomlPath)) {
        Write-Host "❌ Error: $TomlPath not found" -ForegroundColor Red
        return $null
    }
    
    try {
        $Content = Get-Content $TomlPath -Raw
        if ($Content -match 'version\s*=\s*"([^"]+)"') {
            return $Matches[1]
        } elseif ($Content -match "version\s*=\s*'([^']+)'") {
            return $Matches[1]
        } else {
            Write-Host "❌ Error: Could not parse version from $TomlPath" -ForegroundColor Red
            return $null
        }
    } catch {
        Write-Host "❌ Error reading $TomlPath : $($_.Exception.Message)" -ForegroundColor Red
        return $null
    }
}

# Function to check if GitHub CLI is available
function Test-GitHubCLI {
    try {
        $ghVersion = & gh --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ GitHub CLI available" -ForegroundColor Green
            return $true
        }
    } catch {
        # Command not found
    }
    
    Write-Host "❌ GitHub CLI not found. Please install it:" -ForegroundColor Red
    Write-Host "   Visit: https://cli.github.com/" -ForegroundColor Yellow
    Write-Host "   Or run: winget install GitHub.cli" -ForegroundColor Yellow
    return $false
}

# Function to check if authenticated with GitHub
function Test-GitHubAuth {
    try {
        $authResult = & gh auth status 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ GitHub authentication OK" -ForegroundColor Green
            return $true
        }
    } catch {
        # Auth check failed
    }
    
    Write-Host "❌ Not authenticated with GitHub. Please run:" -ForegroundColor Red
    Write-Host "   gh auth login" -ForegroundColor Yellow
    return $false
}

# Main script
Write-Host "=== TaxGlide Release Uploader ===" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
if (-not (Test-GitHubCLI)) { exit 1 }
if (-not (Test-GitHubAuth)) { exit 1 }

# Determine version
if (-not $Version) {
    $Version = Get-ProjectVersion
    if (-not $Version) { 
        Write-Host "Please specify version with -Version parameter" -ForegroundColor Red
        exit 1 
    }
    Write-Host "📋 Auto-detected version: $Version" -ForegroundColor Green
} else {
    Write-Host "📋 Using specified version: $Version" -ForegroundColor Green
}

# Check if release ZIP exists
$ZipPath = "releases\taxglide-v$Version.zip"
if (-not (Test-Path $ZipPath)) {
    Write-Host "❌ Release ZIP not found: $ZipPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Available releases:" -ForegroundColor Yellow
    if (Test-Path "releases") {
        Get-ChildItem "releases\*.zip" | ForEach-Object { 
            Write-Host "  - $($_.Name)" -ForegroundColor White 
        }
    } else {
        Write-Host "  (no releases folder found)" -ForegroundColor Gray
    }
    Write-Host ""
    Write-Host "💡 Build a release first with: .\build_executable.ps1" -ForegroundColor Yellow
    exit 1
}

$ZipSize = (Get-Item $ZipPath).Length / 1MB
Write-Host "✅ Found release ZIP: $ZipPath ($([math]::Round($ZipSize, 2)) MB)" -ForegroundColor Green
Write-Host ""

# Display upload info
Write-Host "📤 Uploading release:" -ForegroundColor Yellow
Write-Host "   Version: v$Version" -ForegroundColor White
Write-Host "   File: $ZipPath" -ForegroundColor White
Write-Host "   Size: $([math]::Round($ZipSize, 2)) MB" -ForegroundColor White
Write-Host "   Notes: $Notes" -ForegroundColor White
Write-Host ""

# Create the release
Write-Host ""
Write-Host "🚀 Creating GitHub release..." -ForegroundColor Yellow

$ReleaseBody = "## TaxGlide v$Version`n`n" +
    "$Notes`n`n" +
    "### 📥 Download`n`n" +
    "**Windows Users:** Download the ZIP file below, extract it, and run the executables.`n`n" +
    "### 🛠️ What's Included`n`n" +
    "- taxglide.exe - Command-line interface`n" +
    "- taxglide_gui.exe - Graphical user interface (recommended)`n" +
    "- configs/ - Tax configuration files for different years`n" +
    "- README.txt - Usage instructions`n`n" +
    "### 🚀 Quick Start`n`n" +
    "1. Download and extract the ZIP file`n" +
    "2. Double-click taxglide_gui.exe to launch the GUI`n" +
    "3. Or use taxglide.exe --help for command-line options`n`n" +
    "---`n`n" +
    "*Released on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') from local build*"

try {
    # Create release with GitHub CLI
    $ReleaseResult = & gh release create "v$Version" $ZipPath `
        --title "TaxGlide v$Version" `
        --notes $ReleaseBody `
        --latest

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "=== 🎉 RELEASE UPLOADED SUCCESSFULLY ===" -ForegroundColor Green
        Write-Host "Version: v$Version" -ForegroundColor White
        Write-Host "File: $ZipPath" -ForegroundColor White
        
        # Get release URL
        try {
            $ReleaseUrl = & gh release view "v$Version" --json url --jq '.url' 2>$null
            if ($ReleaseUrl) {
                Write-Host "Release URL: $ReleaseUrl" -ForegroundColor Cyan
            }
        } catch {
            # URL fetch failed, not critical
        }
        
        Write-Host ""
        Write-Host "✅ Users can now download TaxGlide v$Version from GitHub!" -ForegroundColor Green
    } else {
        Write-Host "❌ Failed to create release" -ForegroundColor Red
        exit 1
    }
    
} catch {
    Write-Host "❌ Error creating release: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
