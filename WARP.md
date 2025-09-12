# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

TaxGlide is a comprehensive Swiss tax calculator and optimizer specifically designed for **St. Gallen (SG) cantonal + Swiss federal taxes**. It uses configuration-driven tax models with advanced deduction optimization algorithms to help users find optimal tax deduction amounts.

## Quick Development Commands

### Installation & Setup
```bash
# Install in development mode
pip install -e .

# Create/activate virtual environment (if needed)
python -m venv .venv
.venv\Scripts\activate  # Windows PowerShell
```

### Running the Application
```bash
# Basic tax calculation
taxglide calc --year 2025 --income 80000

# Find optimal deduction
taxglide optimize --year 2025 --income 80000 --max-deduction 10000

# Validate configuration files
taxglide validate --year 2025

# Generate detailed analysis CSV
taxglide scan --year 2025 --income 85000 --max-deduction 8000

# Create tax curve visualization
taxglide plot --year 2025 --min 50000 --max 150000
```

### Testing & Quality
```bash
# Run all tests
python run_tests.py
# OR
python -m pytest tests/ -v

# Run specific test categories
python run_tests.py calculation
python run_tests.py optimization  
python run_tests.py config

# Run with coverage report
python run_tests.py --coverage

# Type checking (if mypy is installed)
mypy taxglide/

# Code formatting (if black is installed)
black taxglide/
```

## Architecture Overview

### Core Structure
The codebase follows a modular architecture with clear separation of concerns:

```
taxglide/
├── cli.py              # Main CLI interface using Typer
├── engine/             # Core tax calculation logic
│   ├── models.py       # Pydantic models for configuration
│   ├── federal.py      # Swiss federal tax calculations
│   ├── stgallen.py     # St. Gallen cantonal tax calculations
│   ├── multipliers.py  # Tax multiplier system
│   ├── optimize.py     # ROI optimization algorithms
│   └── rounding.py     # Official rounding rules
├── io/                 # Configuration loading
│   └── loader.py       # YAML config loader with validation
└── viz/                # Visualization
    └── curve.py        # Tax curve plotting
```

### Key Architectural Patterns

#### 1. Configuration-Driven Design
Tax rules are externalized in YAML files under `configs/YEAR/`:
- `federal.yaml`: Swiss federal marginal brackets
- `stgallen.yaml`: SG progressive brackets with override rules
- `multipliers.yaml`: Cantonal, communal, and optional multipliers

This design allows updating tax rules without code changes and supports multiple tax years.

#### 2. Decimal Precision
All monetary calculations use Python's `Decimal` type to avoid floating-point precision issues critical in financial calculations.

#### 3. Plugin-Style Tax Models
Each tax type (federal, cantonal) implements its own calculation logic while sharing common interfaces through the `calc_fn` pattern in optimization.

#### 4. Plateau Detection Algorithm
The optimization engine uses sophisticated ROI analysis with plateau detection to find not just the maximum ROI point, but the optimal "sweet spot" - the end of the near-maximum ROI plateau that provides robustness against income fluctuations.

### Tax System Implementation

#### Federal Tax Model
- Marginal bracket system with 100 CHF steps
- Uses ceiling method for rate determination  
- Official ESTV rounding (down to nearest 5 rappen)
- Handles complex bracket transitions for optimization

#### St. Gallen Tax Model  
- Progressive brackets with portion-based calculation
- High-income override (flat 8.5% above 264,200 CHF)
- Additive multiplier system (cantonal + communal factors)
- Supports optional multipliers (fire service, church tax)

#### Optimization Engine
- Coarse + fine-grained ROI scanning
- Plateau detection within configurable tolerance (basis points)
- Federal bracket change detection for micro-optimizations
- Context-aware explanations with "why" reasoning

## Development Patterns

### Path Building Centralization
Following the user's rule preference, path building is centralized in the loader module rather than scattered across scripts. The `CONFIG_ROOT` constant in `cli.py` serves as the single source of truth for configuration paths.

### Error Handling
The CLI uses early validation with clear error messages. The `validate_optimization_inputs()` function catches invalid parameters before expensive calculations begin.

### Type Safety
The codebase extensively uses Pydantic models for configuration validation and type safety, with custom validators for tax-specific business rules.

## Common Development Tasks

### Adding Support for New Cantons
1. Create new YAML configurations in `configs/YEAR/canton_name.yaml`
2. Add calculation logic in `engine/canton_name.py` following the federal/stgallen pattern
3. Update `loader.py` validation rules
4. Add CLI integration in `cli.py`

### Adding New Tax Years
1. Create `configs/YEAR/` directory
2. Copy and modify YAML files with updated tax brackets
3. Run `taxglide validate --year YEAR` to verify
4. Test with known tax scenarios

### Extending Optimization Features
The optimization engine is designed for extensibility:
- Add new ROI tolerance strategies in `optimize.py`
- Implement additional context functions for bracket awareness
- Add new "sweet spot" selection algorithms

### Configuration Validation
The `_validate_configs()` function in `loader.py` performs comprehensive validation:
- Bracket ordering and continuity
- Reasonable value ranges
- Cross-configuration consistency checks
- Gap detection in tax segments

## Key Files to Understand

- `cli.py`: Main entry point - understand the command structure and how calc_fn is passed to optimizer
- `optimize.py`: Core optimization logic - study the plateau detection algorithm
- `models.py`: Data structures - understand the Pydantic validation patterns
- `loader.py`: Configuration validation - critical for maintaining data integrity
- `federal.py` & `stgallen.py`: Tax calculation implementations - models for adding new regions

## Dependencies

Core dependencies (see `pyproject.toml`):
- `typer`: Modern CLI framework
- `rich`: Rich terminal output formatting  
- `pydantic`: Data validation and settings management
- `PyYAML`: Configuration file parsing
- `matplotlib`: Tax curve visualization

The project requires Python 3.11+ and follows modern Python packaging standards with setuptools.

## Test Suite

TaxGlide includes a comprehensive test suite with 39 tests covering:

### Test Categories
- **Calculation Tests** (`test_calculation.py`): Federal tax, SG tax, multipliers, integration
- **Optimization Tests** (`test_optimization.py`): ROI algorithms, plateau detection, edge cases  
- **Configuration Tests** (`test_config_validation.py`): YAML validation, error handling, edge cases

### Key Test Features
- **Real Swiss Tax Validation**: Tests against actual Swiss tax calculations with ≤1 CHF accuracy
- **Bracket Boundary Analysis**: Validates the optimizer's ability to find bracket transition opportunities
- **Positive & Negative Testing**: Both functional tests and validation error detection
- **Edge Case Coverage**: Boundary conditions, bracket transitions, high-income scenarios
- **Sophisticated Algorithm Testing**: ROI optimization, plateau detection, tolerance settings
- **Configuration Validation**: All YAML rules and constraints thoroughly tested
- **Integration Testing**: End-to-end calculation pipeline validation

### Running Tests
Use the convenient test runner: `python run_tests.py --verbose`

## Critical Development Workflow

### ⚠️ MANDATORY: Always Run Tests Before Git Operations

**NEVER run `git add` and `git push` without running the test suite first!**

```bash
# REQUIRED workflow for any code changes:

# 1. Make your changes
# 2. Run the full test suite
python -m pytest tests/ -v
# OR
python run_tests.py --verbose

# 3. Only if ALL tests pass, then:
git add .
git commit -m "Your commit message"
git push
```

**Why this is critical:**
- TaxGlide handles financial calculations where precision matters
- 64 comprehensive tests validate against real Swiss tax scenarios
- Regressions could result in incorrect tax calculations
- Tests catch integration issues between modules
- Ensures configuration changes don't break existing functionality

**If any test fails:**
1. Fix the issue before committing
2. Re-run tests to confirm the fix
3. Never commit broken code

## Important Notes

- Comprehensive test suite with 39 tests including real Swiss tax value validation (≤1 CHF accuracy)
- The codebase was primarily written with AI assistance (ChatGPT-5 and Claude)
- All calculations follow official Swiss tax rules and rounding methods
- Configuration files must be validated after any changes using `taxglide validate`
- The optimization algorithm prioritizes conservative recommendations (end of plateau) over pure maximum ROI
- Tests serve as documentation for expected behavior and edge cases
