# TaxGlide Nuitka Build Script
# Centralized configuration for building optimized executable

# Configuration - All paths and settings in one place
$BuildConfig = @{
    # Input/Output paths
    MainScript = "main.py"
    OutputDir = "dist"
    OutputName = "taxglide"
    
    # Nuitka optimization settings
    OptimizationLevel = "max"
    
    # Include/exclude patterns for data files
    IncludeDataDirs = @("configs")
    
    # Python path settings
    PythonPath = ".\.venv\Scripts\python.exe"
    
    # Build cleanup
    CleanBuild = $true
    
    # Release packaging settings
    CreateRelease = $true
    ReleaseDir = "releases"
    ProjectTomlPath = "pyproject.toml"
    ReleaseFiles = @("configs")  # Additional files/folders to include in release
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
        [string]$ExecutablePath,
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
    
    # Copy executable
    if (Test-Path $ExecutablePath) {
        Copy-Item $ExecutablePath $VersionedReleasePath
        Write-Host "Copied executable: $(Split-Path $ExecutablePath -Leaf)" -ForegroundColor Green
    } else {
        throw "Executable not found: $ExecutablePath"
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
    $ReadmeContent = @"
TaxGlide v$Version - Portable Release
====================================

This is a portable release of TaxGlide, a Swiss tax calculator CLI.

Files included:
- taxglide.exe: Main executable (no Python installation required)
- configs/: Tax configuration files for different years

Usage:
  taxglide.exe --help                     # Show available commands
  taxglide.exe calc --year 2025 --income 100000  # Calculate taxes
  taxglide.exe validate --year 2025       # Validate configurations

For more information, visit: https://github.com/csarwi/taxglide

Built on: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Platform: Windows x64
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

# Function to run tests before building
function Test-TaxGlide {
    Write-Host "=== Running Tests Before Build ===" -ForegroundColor Cyan
    Write-Host "Ensuring code quality before building..." -ForegroundColor Yellow
    
    try {
        # Run the test suite using run_tests.py
        $TestProcess = Start-Process -FilePath $BuildConfig.PythonPath -ArgumentList @("run_tests.py") -Wait -PassThru -NoNewWindow
        
        if ($TestProcess.ExitCode -eq 0) {
            Write-Host "✅ All tests passed - proceeding with build" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ Tests failed - build cancelled" -ForegroundColor Red
            Write-Host "Please fix failing tests before building" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "❌ Error running tests: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main build function
function Build-TaxGlide {
    Write-Host "=== TaxGlide Nuitka Build Process ===" -ForegroundColor Cyan
    
    # Run tests first
    if (-not (Test-TaxGlide)) {
        Write-Host "Build aborted due to test failures" -ForegroundColor Red
        return $false
    }
    
    Write-Host "Starting build with optimized settings..." -ForegroundColor Yellow
    
    # Ensure output directory exists
    $OutputPath = Get-BuildPath $BuildConfig.OutputDir
    Ensure-Directory $OutputPath
    
    # Clean previous build if requested
    if ($BuildConfig.CleanBuild) {
        Write-Host "Cleaning previous build artifacts..." -ForegroundColor Yellow
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
                Write-Host "Testing executable..." -ForegroundColor Yellow
                & $FinalExe --help
                
                # Create release package if configured
                if ($BuildConfig.CreateRelease) {
                    Write-Host "" 
                    try {
                        $Version = Get-ProjectVersion $BuildConfig.ProjectTomlPath
                        Write-Host "Detected version: $Version" -ForegroundColor Green
                        
                        $ReleaseResult = Create-ReleasePackage -ExecutablePath $FinalExe -Version $Version -ReleaseDir $BuildConfig.ReleaseDir -AdditionalFiles $BuildConfig.ReleaseFiles
                        
                        if ($ReleaseResult.success) {
                            Write-Host "" 
                            Write-Host "=== RELEASE SUMMARY ===" -ForegroundColor Green
                            Write-Host "Version: $($ReleaseResult.version)" -ForegroundColor White
                            Write-Host "Release ZIP: $($ReleaseResult.zip_path)" -ForegroundColor White
                            Write-Host "ZIP Size: $($ReleaseResult.zip_size_mb) MB" -ForegroundColor White
                            Write-Host "Release ready for distribution!" -ForegroundColor Green
                        } else {
                            Write-Host "Warning: Release packaging failed: $($ReleaseResult.error)" -ForegroundColor Yellow
                        }
                    } catch {
                        Write-Host "Warning: Release packaging failed: $($_.Exception.Message)" -ForegroundColor Yellow
                    }
                }
                
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
    
    # Verify we're in the right directory
    if (-not (Test-Path $BuildConfig.MainScript)) {
        Write-Host "Error: Main script '$($BuildConfig.MainScript)' not found in current directory." -ForegroundColor Red
        Write-Host "Please run this script from the TaxGlide project root." -ForegroundColor Red
        exit 1
    }
    
    # Check if virtual environment is activated
    if (-not (Test-Path $BuildConfig.PythonPath)) {
        Write-Host "Error: Python executable not found at '$($BuildConfig.PythonPath)'" -ForegroundColor Red
        Write-Host "Please ensure the virtual environment is set up correctly." -ForegroundColor Red
        exit 1
    }
    
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
