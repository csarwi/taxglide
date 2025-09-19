# TaxGlide Build Script - EXECUTABLE CREATION ONLY
# Builds standalone CLI and/or GUI executables from existing source code
# 
# PREREQUISITES (this script does NOT install these):
#   - Virtual environment with required packages already installed
#   - Nuitka installed in the virtual environment
#   - Node.js/npm for GUI builds
#
# Usage:
#   .\build_executable.ps1                  # Build both CLI and GUI (default)
#   .\build_executable.ps1 -BuildTarget cli  # Build CLI only
#   .\build_executable.ps1 -BuildTarget gui  # Build GUI only
#   .\build_executable.ps1 -BuildTarget both # Build both (explicit)

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('cli', 'gui', 'both')]
    [string]$BuildTarget = 'both',
    
    [Parameter(Mandatory=$false)]
    [switch]$UploadToGitHub,
    
    [Parameter(Mandatory=$false)]
    [string]$ReleaseNotes = "Latest TaxGlide release with new features and improvements."
)

# Configuration - All paths and settings in one place
$BuildConfig = @{
    # Build targets
    BuildTarget = $BuildTarget
    BuildCLI = ($BuildTarget -eq 'cli' -or $BuildTarget -eq 'both')
    BuildGUI = ($BuildTarget -eq 'gui' -or $BuildTarget -eq 'both')
    
    # Input/Output paths
    MainScript = "main.py"
    OutputDir = "dist"
    OutputName = "taxglide"
    
    # Nuitka optimization settings
    OptimizationLevel = "max"
    
    # Include/exclude patterns for data files
    IncludeDataDirs = @("taxglide/configs")
    
    # Python path settings
    PythonPath = ".\.venv\Scripts\python.exe"
    
    # Build cleanup
    CleanBuild = $true
    
    # GUI build settings
    GuiDir = "gui"
    GuiOutputName = "taxglide_gui"
    
    # Release packaging settings
    CreateRelease = $true
    ReleaseDir = "releases"
    ProjectTomlPath = "pyproject.toml"
    ReleaseFiles = @("taxglide/configs")  # Additional files/folders to include in release
}

# Function to build paths consistently
function Get-BuildPath {
    param([string]$RelativePath)
    return Join-Path (Get-Location) $RelativePath
}

# Function to ensure directory exists
function Ensure-Directory {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
        Write-Host "Created directory: $Path" -ForegroundColor Green
    }
}

# Function to extract version from pyproject.toml
function Get-ProjectVersion {
    param([string]$TomlPath)
    if (-not (Test-Path $TomlPath)) {
        Write-Host "Warning: $TomlPath not found, using default version 0.1.0" -ForegroundColor Yellow
        return "0.1.0"
    }
    
    try {
        $Content = Get-Content $TomlPath -Raw
        if ($Content -match 'version\s*=\s*"([^"]+)"') {
            return $Matches[1]
        } elseif ($Content -match "version\s*=\s*'([^']+)'") {
            return $Matches[1]
        } else {
            Write-Host "Warning: Could not parse version from $TomlPath, using default 0.1.0" -ForegroundColor Yellow
            return "0.1.0"
        }
    } catch {
        Write-Host "Error reading $TomlPath : $($_.Exception.Message)" -ForegroundColor Red
        return "0.1.0"
    }
}

# Function to create release package
function Create-ReleasePackage {
    param(
        [array]$ExecutablePaths,
        [string]$Version,
        [string]$ReleaseDir,
        [array]$AdditionalFiles
    )
    
    Write-Host "=== Creating Release Package ===" -ForegroundColor Cyan
    
    # Create release directory structure
    $ReleaseBasePath = Get-BuildPath $ReleaseDir
    $VersionedReleasePath = Join-Path $ReleaseBasePath "taxglide-v$Version"
    $ZipFileName = "taxglide-v$Version.zip"
    $ZipPath = Join-Path $ReleaseBasePath $ZipFileName
    
    Ensure-Directory $ReleaseBasePath
    Ensure-Directory $VersionedReleasePath
    
    # Clean up previous release of same version
    if (Test-Path $VersionedReleasePath) {
        Remove-Item $VersionedReleasePath -Recurse -Force
        Write-Host "Cleaned previous release: $VersionedReleasePath" -ForegroundColor Green
    }
    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath -Force
        Write-Host "Removed previous zip: $ZipPath" -ForegroundColor Green
    }
    
    # Create fresh release directory
    New-Item -ItemType Directory -Path $VersionedReleasePath -Force | Out-Null
    
    # Copy all executables
    foreach ($ExecutablePath in $ExecutablePaths) {
        if (Test-Path $ExecutablePath) {
            Copy-Item $ExecutablePath $VersionedReleasePath
            Write-Host "Copied executable: $(Split-Path $ExecutablePath -Leaf)" -ForegroundColor Green
        } else {
            Write-Host "Warning: Executable not found: $ExecutablePath" -ForegroundColor Yellow
        }
    }
    
    # Copy additional files/directories
    foreach ($item in $AdditionalFiles) {
        $sourcePath = Get-BuildPath $item
        if (Test-Path $sourcePath) {
            $destPath = Join-Path $VersionedReleasePath $item
            if (Test-Path $sourcePath -PathType Container) {
                # Copy directory
                Copy-Item $sourcePath $destPath -Recurse -Force
                Write-Host "Copied directory: $item" -ForegroundColor Green
            } else {
                # Copy file
                Copy-Item $sourcePath $destPath -Force
                Write-Host "Copied file: $item" -ForegroundColor Green
            }
        } else {
            Write-Host "Warning: Release file not found: $sourcePath" -ForegroundColor Yellow
        }
    }
    
    # Create README for the release
    $CliIncluded = Test-Path (Join-Path $VersionedReleasePath "taxglide.exe")
    $GuiIncluded = Test-Path (Join-Path $VersionedReleasePath "taxglide_gui.exe")
    
    $FilesSection = "Files included:`n- configs/: Tax configuration files for different years`n"
    $UsageSection = "Usage:`n"
    
    if ($CliIncluded) {
        $FilesSection += "- taxglide.exe: Command-line interface (no Python installation required)`n"
        $UsageSection += "  taxglide.exe --help                     # Show CLI commands`n"
        $UsageSection += "  taxglide.exe calc --year 2025 --income 100000  # Calculate taxes`n"
        $UsageSection += "  taxglide.exe optimize --year 2025 --income 80000 --max-deduction 5000  # Optimize deductions`n"
        $UsageSection += "  taxglide.exe validate --year 2025       # Validate configurations`n"
    }
    
    if ($GuiIncluded) {
        $FilesSection += "- taxglide_gui.exe: Graphical user interface`n"
        $UsageSection = "  taxglide_gui.exe                        # Launch GUI (recommended)`n" + $UsageSection
    }
    
    $ReadmeContent = @"
TaxGlide v$Version - Portable Release
====================================

This is a portable release of TaxGlide, a Swiss tax calculator.

$FilesSection
$UsageSection
For more information, visit: https://github.com/csarwi/taxglide

Built on: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Platform: Windows x64
Build Target: $($BuildConfig.BuildTarget)
"@
    
    $ReadmePath = Join-Path $VersionedReleasePath "README.txt"
    Set-Content -Path $ReadmePath -Value $ReadmeContent -Encoding UTF8
    Write-Host "Created README.txt" -ForegroundColor Green
    
    # Create ZIP archive
    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory($VersionedReleasePath, $ZipPath)
        
        $ZipSize = (Get-Item $ZipPath).Length / 1MB
        Write-Host "=== RELEASE PACKAGE CREATED ===" -ForegroundColor Green
        Write-Host "Release directory: $VersionedReleasePath" -ForegroundColor Green
        Write-Host "Release ZIP: $ZipPath" -ForegroundColor Green
        Write-Host "ZIP size: $([math]::Round($ZipSize, 2)) MB" -ForegroundColor Green
        
        return @{
            "success" = $true
            "version" = $Version
            "zip_path" = $ZipPath
            "release_dir" = $VersionedReleasePath
            "zip_size_mb" = [math]::Round($ZipSize, 2)
        }
    } catch {
        Write-Host "Error creating ZIP archive: $($_.Exception.Message)" -ForegroundColor Red
        return @{"success" = $false; "error" = $_.Exception.Message}
    }
}

# Function to build GUI with Tauri
function Build-GUI {
    Write-Host "=== Building TaxGlide GUI ===" -ForegroundColor Cyan
    
    $GuiPath = Get-BuildPath $BuildConfig.GuiDir
    if (-not (Test-Path $GuiPath)) {
        Write-Host "Error: GUI directory not found: $GuiPath" -ForegroundColor Red
        return $false
    }
    
    # Check if npm is available
    try {
        $NpmVersion = & npm --version 2>$null
        Write-Host "Found npm version: $NpmVersion" -ForegroundColor Green
    } catch {
        Write-Host "Error: npm not found. Please install Node.js" -ForegroundColor Red
        return $false
    }
    
    # Navigate to GUI directory
    $OriginalDir = Get-Location
    try {
        Set-Location $GuiPath
        
        Write-Host "Installing GUI dependencies..." -ForegroundColor Yellow
        $InstallResult = & cmd /c "npm install" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: npm install failed" -ForegroundColor Red
            Write-Host "Output: $InstallResult" -ForegroundColor Red
            return $false
        }
        
        Write-Host "Building GUI with Tauri..." -ForegroundColor Yellow
        $BuildResult = & cmd /c "npm run tauri build" 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Tauri build failed" -ForegroundColor Red
            Write-Host "Output: $BuildResult" -ForegroundColor Red
            return $false
        }
        
        # Find the built executable (Tauri uses package name from Cargo.toml)
        $TauriOutputDir = Join-Path $GuiPath "src-tauri\target\release"
        $TauriExeName = "taxglide-gui.exe"  # This matches the name in Cargo.toml
        $TauriExePath = Join-Path $TauriOutputDir $TauriExeName
        $GuiExePath = $TauriExePath
        
        if (Test-Path $GuiExePath) {
            $FileSize = (Get-Item $GuiExePath).Length / 1MB
            Write-Host "=== GUI BUILD SUCCESSFUL ===" -ForegroundColor Green
            Write-Host "GUI executable created: $GuiExePath" -ForegroundColor Green
            Write-Host "File size: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Green
            
            # Copy GUI executable to main project dist directory
            $MainProjectRoot = Split-Path $GuiPath -Parent  # Go up one level from gui/ to project root
            $MainDistDir = Join-Path $MainProjectRoot "dist"
            $DistGuiPath = Join-Path $MainDistDir "$($BuildConfig.GuiOutputName).exe"
            Copy-Item $GuiExePath $DistGuiPath -Force
            Write-Host "Copied GUI to main dist: $DistGuiPath" -ForegroundColor Green
            
            return $true
        } else {
            Write-Host "Error: GUI executable not found at expected location: $GuiExePath" -ForegroundColor Red
            return $false
        }
        
    } catch {
        Write-Host "Error during GUI build: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    } finally {
        Set-Location $OriginalDir
    }
}

# Function to verify Python environment is ready (but don't install anything)
function Test-BuildEnvironment {
    Write-Host "=== Verifying Build Environment ===" -ForegroundColor Cyan
    
    # Check if Python executable exists
    if (-not (Test-Path $BuildConfig.PythonPath)) {
        Write-Host "❌ Python executable not found at: $($BuildConfig.PythonPath)" -ForegroundColor Red
        Write-Host "Please ensure the virtual environment is set up correctly." -ForegroundColor Red
        return $false
    }
    
    # Check if Nuitka is available
    try {
        $NuitkaCheck = & $BuildConfig.PythonPath -m nuitka --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Nuitka available" -ForegroundColor Green
        } else {
            Write-Host "❌ Nuitka not available. Please install with: pip install nuitka" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Error checking Nuitka: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
    
    # Check if main script exists
    if (-not (Test-Path $BuildConfig.MainScript)) {
        Write-Host "❌ Main script not found: $($BuildConfig.MainScript)" -ForegroundColor Red
        return $false
    }
    
    # Check if config directories exist
    foreach ($dataDir in $BuildConfig.IncludeDataDirs) {
        if (-not (Test-Path $dataDir)) {
            Write-Host "❌ Data directory not found: $dataDir" -ForegroundColor Red
            return $false
        }
    }
    
    Write-Host "✅ Build environment ready" -ForegroundColor Green
    return $true
}

# Main build function
function Build-TaxGlide {
    Write-Host "=== TaxGlide Build Process (Target: $($BuildConfig.BuildTarget)) ===" -ForegroundColor Cyan
    
    # Verify build environment first
    if (-not (Test-BuildEnvironment)) {
        Write-Host "Build aborted due to environment issues" -ForegroundColor Red
        return $false
    }
    
    $BuildResults = @{
        "CLI" = $null
        "GUI" = $null
        "Overall" = $false
    }
    
    # Ensure output directory exists
    $OutputPath = Get-BuildPath $BuildConfig.OutputDir
    Ensure-Directory $OutputPath
    
    # Build CLI if requested
    if ($BuildConfig.BuildCLI) {
        Write-Host "=== Building CLI ===" -ForegroundColor Cyan
        $BuildResults.CLI = Build-CLI
    } else {
        Write-Host "Skipping CLI build (target: $($BuildConfig.BuildTarget))" -ForegroundColor Yellow
        $BuildResults.CLI = $true  # Mark as success since it wasn't requested
    }
    
    # Build GUI if requested
    if ($BuildConfig.BuildGUI) {
        if ($BuildConfig.BuildCLI -and -not $BuildResults.CLI) {
            Write-Host "Skipping GUI build due to CLI build failure" -ForegroundColor Yellow
            $BuildResults.GUI = $false
        } else {
            Write-Host "=== Building GUI ===" -ForegroundColor Cyan
            $BuildResults.GUI = Build-GUI
        }
    } else {
        Write-Host "Skipping GUI build (target: $($BuildConfig.BuildTarget))" -ForegroundColor Yellow
        $BuildResults.GUI = $true  # Mark as success since it wasn't requested
    }
    
    # Determine overall success
    $BuildResults.Overall = $BuildResults.CLI -and $BuildResults.GUI
    
    # Create release package if configured and builds were successful
    if ($BuildConfig.CreateRelease -and $BuildResults.Overall) {
        Write-Host "" 
        try {
            $Version = Get-ProjectVersion $BuildConfig.ProjectTomlPath
            Write-Host "Detected version: $Version" -ForegroundColor Green
            
            # Determine which executables to include
            $ExecutablesToInclude = @()
            if ($BuildConfig.BuildCLI) {
                $ExecutablesToInclude += Join-Path $OutputPath "$($BuildConfig.OutputName).exe"
            }
            if ($BuildConfig.BuildGUI) {
                $ExecutablesToInclude += Join-Path $OutputPath "$($BuildConfig.GuiOutputName).exe"
            }
            
            if ($ExecutablesToInclude.Count -gt 0) {
                $ReleaseResult = Create-ReleasePackage -ExecutablePaths $ExecutablesToInclude -Version $Version -ReleaseDir $BuildConfig.ReleaseDir -AdditionalFiles $BuildConfig.ReleaseFiles
                
                if ($ReleaseResult.success) {
                    Write-Host "" 
                    Write-Host "=== RELEASE SUMMARY ===" -ForegroundColor Green
                    Write-Host "Version: $($ReleaseResult.version)" -ForegroundColor White
                    Write-Host "Target: $($BuildConfig.BuildTarget)" -ForegroundColor White
                    Write-Host "Release ZIP: $($ReleaseResult.zip_path)" -ForegroundColor White
                    Write-Host "ZIP Size: $($ReleaseResult.zip_size_mb) MB" -ForegroundColor White
                    Write-Host "Release ready for distribution!" -ForegroundColor Green
                    
                    # Upload to GitHub if requested
                    if ($UploadToGitHub) {
                        Write-Host "" 
                        Write-Host "🚀 Uploading to GitHub..." -ForegroundColor Yellow
                        try {
                            $UploadScriptPath = Join-Path (Get-Location) "upload-release.ps1"
                            if (Test-Path $UploadScriptPath) {
                                & $UploadScriptPath -Version $ReleaseResult.version -Notes $ReleaseNotes
                                if ($LASTEXITCODE -eq 0) {
                                    Write-Host "✅ Successfully uploaded to GitHub!" -ForegroundColor Green
                                } else {
                                    Write-Host "❌ GitHub upload failed" -ForegroundColor Red
                                }
                            } else {
                                Write-Host "❌ Upload script not found: $UploadScriptPath" -ForegroundColor Red
                            }
                        } catch {
                            Write-Host "❌ Error during GitHub upload: $($_.Exception.Message)" -ForegroundColor Red
                        }
                    }
                } else {
                    Write-Host "Warning: Release packaging failed: $($ReleaseResult.error)" -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "Warning: Release packaging failed: $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
    
    return $BuildResults.Overall
}

# Function to build CLI with Nuitka
function Build-CLI {
    Write-Host "Starting CLI build with optimized settings..." -ForegroundColor Yellow
    
    $OutputPath = Get-BuildPath $BuildConfig.OutputDir
    
    # Clean previous build if requested
    if ($BuildConfig.CleanBuild) {
        Write-Host "Cleaning previous CLI build artifacts..." -ForegroundColor Yellow
        $ExePath = Join-Path $OutputPath "$($BuildConfig.OutputName).exe"
        if (Test-Path $ExePath) {
            Remove-Item $ExePath -Force
            Write-Host "Removed: $ExePath" -ForegroundColor Green
        }
        
        # Clean Nuitka cache
        $CacheDir = Get-BuildPath "$($BuildConfig.OutputName).build"
        if (Test-Path $CacheDir) {
            Remove-Item $CacheDir -Recurse -Force
            Write-Host "Cleaned build cache: $CacheDir" -ForegroundColor Green
        }
    }
    
    # Build the Nuitka command with all optimizations
    $NuitkaArgs = @(
        "-m"
        "nuitka"
        
        # Core compilation settings
        "--onefile"                    # Single executable file
        "--standalone"                 # Standalone distribution
        
        # Optimization settings for lean, small executable
        "--assume-yes-for-downloads"   # Auto-download dependencies
        "--enable-plugin=anti-bloat"   # Remove unnecessary modules
        
        # Performance optimizations
        "--lto=yes"                    # Link Time Optimization
        
        # Output configuration
        "--output-dir=$OutputPath"
        "--output-filename=$($BuildConfig.OutputName).exe"
        
        # Windows-specific optimizations  
        "--msvc=latest"                # Use latest MSVC for Python 3.13 compatibility
        "--enable-plugin=implicit-imports"  # Auto-detect imports
        
        # Remove debugging info for smaller size  
        "--remove-output"              # Clean up intermediate files
        
        # Source file
        $BuildConfig.MainScript
    )
    
    # Add optimization level if max
    if ($BuildConfig.OptimizationLevel -eq "max") {
        $NuitkaArgs += "--python-flag=no_asserts"       # Maximum Python optimization
        $NuitkaArgs += "--python-flag=no_docstrings"   # Remove docstrings for smaller size
    }
    
    # Add data directories
    foreach ($dataDir in $BuildConfig.IncludeDataDirs) {
        $NuitkaArgs += "--include-data-dir=$dataDir=$dataDir"
    }
    
    Write-Host "Executing Nuitka with the following optimizations:" -ForegroundColor Green
    Write-Host "- Single file executable (--onefile)" -ForegroundColor White
    Write-Host "- Anti-bloat plugin enabled" -ForegroundColor White
    Write-Host "- Link Time Optimization enabled" -ForegroundColor White
    Write-Host "- Latest MSVC compiler for Python 3.13 compatibility" -ForegroundColor White
    Write-Host "- Maximum Python optimization level" -ForegroundColor White
    Write-Host "- Including configs directory" -ForegroundColor White
    Write-Host ""
    
    # Execute the build
    try {
        Write-Host "Running command: $($BuildConfig.PythonPath) $($NuitkaArgs -join ' ')" -ForegroundColor Gray
        
        $Process = Start-Process -FilePath $BuildConfig.PythonPath -ArgumentList $NuitkaArgs -Wait -PassThru -NoNewWindow
        
        # Check if the executable was created successfully (sometimes exit code is wrong)
        $FinalExe = Join-Path $OutputPath "$($BuildConfig.OutputName).exe"
        if (Test-Path $FinalExe) {
                $FileSize = (Get-Item $FinalExe).Length / 1MB
                Write-Host "=== BUILD SUCCESSFUL ===" -ForegroundColor Green
                Write-Host "Executable created: $FinalExe" -ForegroundColor Green
                Write-Host "File size: $([math]::Round($FileSize, 2)) MB" -ForegroundColor Green
                
                # Test the executable
                Write-Host ""
                Write-Host "Testing CLI executable..." -ForegroundColor Yellow
                & $FinalExe --help
                
                return $true
        } else {
            Write-Host "=== BUILD FAILED ===" -ForegroundColor Red
            Write-Host "Executable not found at expected location: $FinalExe" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "=== BUILD ERROR ===" -ForegroundColor Red
        Write-Host "Error during build: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to show build configuration
function Show-BuildConfig {
    Write-Host "=== Build Configuration ===" -ForegroundColor Cyan
    $BuildConfig.GetEnumerator() | Sort-Object Name | ForEach-Object {
        if ($_.Value -is [array]) {
            Write-Host "$($_.Key): $($_.Value -join ', ')" -ForegroundColor White
        } else {
            Write-Host "$($_.Key): $($_.Value)" -ForegroundColor White
        }
    }
    
    # Show detected version
    if ($BuildConfig.CreateRelease) {
        $DetectedVersion = Get-ProjectVersion $BuildConfig.ProjectTomlPath
        Write-Host "Detected Version: $DetectedVersion" -ForegroundColor Cyan
    }
    
    Write-Host ""
}

# Main execution
if ($MyInvocation.InvocationName -ne '.') {
    Show-BuildConfig
    
    # Environment checks are now handled in Test-BuildEnvironment
    
    # Start the build
    $Success = Build-TaxGlide
    
    if ($Success) {
        Write-Host ""
        Write-Host "=== BUILD COMPLETE ===" -ForegroundColor Green
        Write-Host "Your optimized TaxGlide executable is ready!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host ""
        Write-Host "Build failed. Please check the error messages above." -ForegroundColor Red
        exit 1
    }
}
