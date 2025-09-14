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

# Main build function
function Build-TaxGlide {
    Write-Host "=== TaxGlide Nuitka Build Process ===" -ForegroundColor Cyan
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
                
                return $true
            } else {
                Write-Host "=== BUILD FAILED ===" -ForegroundColor Red
                Write-Host "Executable not found at expected location: $FinalExe" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "=== BUILD FAILED ===" -ForegroundColor Red
            Write-Host "Nuitka process exited with code: $($Process.ExitCode)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "=== BUILD ERROR ===" -ForegroundColor Red
        Write-Host "Error during build: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Function to show build configuration
function Show-BuildConfig {
    Write-Host "=== Build Configuration ===" -ForegroundColor Cyan
    $BuildConfig.GetEnumerator() | Sort-Object Name | ForEach-Object {
        Write-Host "$($_.Key): $($_.Value)" -ForegroundColor White
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
