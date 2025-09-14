# TaxGlide Executable Build Guide

This directory contains everything needed to build TaxGlide into a lean, optimized executable using Nuitka.

## Quick Start

### Option 1: Using the Batch File (Simplest)
```cmd
build.bat
```

### Option 2: Using PowerShell Directly
```powershell
.\build_executable.ps1
```

### Option 3: Manual Nuitka Command
```powershell
python -m nuitka --onefile --standalone --assume-yes-for-downloads --enable-plugin=anti-bloat --lto=yes --output-dir=dist --output-filename=taxglide.exe --msvc=latest --enable-plugin=implicit-imports --remove-output main.py --python-flag=no_asserts --python-flag=no_docstrings --include-data-dir=configs=configs
```

## Prerequisites

1. **Virtual Environment**: Ensure your `.venv` is activated
2. **Dependencies**: Install with `pip install -e .`
3. **Nuitka**: Install with `pip install nuitka`
4. **MSVC**: Visual Studio Build Tools or Visual Studio installed (for Python 3.13 compatibility)

## Build Configuration

The build is centrally configured in `build_executable.ps1` with the following optimizations:

### Performance Optimizations
- **Single file executable** (`--onefile`): Everything packed into one .exe
- **Standalone distribution** (`--standalone`): No Python installation required
- **Link Time Optimization** (`--lto=yes`): Better performance and smaller size
- **Anti-bloat plugin**: Removes unnecessary modules automatically
- **Python optimizations**: Removes docstrings and assertions

### Compiler Settings
- **MSVC Latest**: Uses latest Visual Studio compiler (Python 3.13 compatible)
- **Implicit imports**: Auto-detects and includes required modules
- **Data file inclusion**: Embeds the `configs` directory

### Build Artifacts
- **Output**: `dist/taxglide.exe` (~33.4 MB)
- **Temporary files**: Automatically cleaned up
- **Build cache**: Reused for faster subsequent builds

## Build Configuration Customization

Edit `build_executable.ps1` to modify:

```powershell
$BuildConfig = @{
    MainScript = "main.py"           # Entry point
    OutputDir = "dist"               # Output directory
    OutputName = "taxglide"          # Executable name
    OptimizationLevel = "max"        # max, standard, or debug
    IncludeDataDirs = @("configs")   # Data directories to embed
    PythonPath = ".\.venv\Scripts\python.exe"
    CleanBuild = $true               # Clean previous builds
}
```

## Troubleshooting

### Python 3.13 Compatibility
- **Issue**: MinGW64 not supported with Python 3.13
- **Solution**: Script automatically uses `--msvc=latest`
- **Requirements**: Visual Studio Build Tools must be installed

### Missing Dependencies
```powershell
pip install -e .
pip install nuitka
```

### Build Cache Issues
The script automatically cleans build artifacts. For manual cleanup:
```powershell
Remove-Item -Recurse -Force dist
Remove-Item -Recurse -Force *.build
```

### Large File Size
Current size (~33.4 MB) includes:
- Python runtime
- All dependencies (typer, rich, pydantic, matplotlib, etc.)
- Configuration files
- Anti-bloat optimizations already applied

For smaller size, consider:
- Removing matplotlib if plotting isn't needed
- Using `--standalone` without `--onefile` for distributed deployment

## Performance Notes

- **First run**: May be slightly slower due to extraction (onefile mode)
- **Subsequent runs**: Normal performance
- **Startup time**: ~1-2 seconds (includes self-extraction)
- **Memory usage**: Similar to regular Python execution

## Distribution

The resulting `dist/taxglide.exe` is:
- ✅ Fully portable (no Python installation required)
- ✅ Self-contained (all dependencies included)
- ✅ Configuration-embedded (configs directory included)
- ✅ Windows compatible (tested on Windows 10+)

Simply copy `taxglide.exe` to any Windows machine and run it directly.

## Files Created by Build Process

- `main.py` - Entry point for Nuitka compilation
- `build_executable.ps1` - Main build script with centralized configuration
- `build.bat` - Simple wrapper for easier execution
- `dist/taxglide.exe` - Final executable (~33.4 MB)
- `BUILD.md` - This documentation file

## Centralized Path Management

Following the user's preference for centralized path building, all paths are managed in the `$BuildConfig` hashtable at the top of the build script. This avoids inconsistencies and makes the build configuration easy to maintain and modify.
