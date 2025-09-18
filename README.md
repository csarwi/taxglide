# TaxGlide 🇨🇭

TaxGlide is a comprehensive Swiss tax calculator and optimizer for Swiss federal and cantonal taxes. It supports multiple cantons and municipalities, each with their own tax rules and multipliers. Available both as a powerful CLI tool and as a modern desktop GUI application.

The project was born from the idea of finding the optimal level of pension fund buy-ins — exploring where the ROI lies and how to structure multi-year deductions to maximize tax savings.

Built on configuration-driven tax models and advanced deduction optimization algorithms, TaxGlide helps you plan ahead with precision.

Almost entirely written with the support of ChatGPT-5 and Claude.

## Features

### 💱 Core Tax Engine
- **Multi-Canton Support**: Federal + multiple canton/municipality combinations 🆕
- **Accurate Swiss Tax Models**: Federal (marginal brackets) + cantonal (progressive + multipliers)
- **Married Joint Filing Support**: Income splitting for married couples per Swiss tax law
- **Separate Income Support**: Different taxable incomes for cantonal and Federal taxes
- **Smart Deduction Optimization**: Find optimal deduction amounts using ROI analysis with plateau detection
- **Flexible Multiplier System**: Municipality-specific multipliers (cantonal, municipal, fire service, church)
- **Configuration-Driven**: Easy to update tax rules and add new locations via unified YAML configuration

### 🖥️ Desktop GUI Application
- **Modern Interface**: Beautiful Tauri-based desktop app with native performance
- **Interactive Calculator**: Real-time tax calculations with detailed breakdowns
- **Advanced Optimizer**: Visual deduction optimization with comprehensive results
- **Interactive Scanner**: 🆕 **Sexy data table** with sorting, filtering, and search for exploring deduction scenarios
- **Color-coded Results**: Visual indicators for ROI, tax savings, and marginal rates
- **Responsive Design**: Clean, professional interface that scales beautifully
- **Cross-platform**: Runs natively on Windows, macOS, and Linux

### 💻 Command Line Interface  
- **Rich CLI Commands**: Multiple commands for calculation, optimization, scanning, and visualization
- **Enhanced Output**: Detailed income breakdowns when using separate SG/Federal incomes 🆕
- **Export Capabilities**: JSON output and CSV scanning for analysis
- **Backward Compatible**: All existing workflows continue to work unchanged

## Installation

### CLI Installation
```bash
pip install -e .
```

### GUI Application

#### Development Mode
```bash
cd gui
npm install
npm run tauri dev
```

#### Production Build
```bash
cd gui
npm install
npm run tauri build
```

The GUI provides an intuitive interface for all TaxGlide functionality with interactive tables, real-time calculations, and visual optimization results.

## Testing & Development

⚠️ **IMPORTANT: Always run tests before building or deploying!**

TaxGlide includes a comprehensive test suite with 71 tests that validate calculations against real Swiss tax values with ≤1 CHF accuracy, including married joint filing scenarios.

### Run Tests (Verbose)

```bash
# Recommended: Use the convenient test runner (verbose output)
python run_tests.py --verbose

# Alternative: Direct pytest with verbose output
python -m pytest tests/ -v

# With detailed output and no capture (shows all print statements)
python -m pytest tests/ -v -s
```

### Run Specific Test Categories

```bash
# Test only calculations (federal, SG, multipliers, integration)
python run_tests.py calculation --verbose

# Test only optimization algorithms (ROI, plateau detection, bracket analysis)
python run_tests.py optimization --verbose

# Test only configuration validation (YAML validation, error handling)
python run_tests.py config --verbose
```

### Run Tests with Coverage

```bash
# See test coverage report
python run_tests.py --coverage

# Or with pytest-cov directly
python -m pytest tests/ --cov=taxglide --cov-report=term-missing
```

### Development Workflow

**Before every build/commit/deploy:**

```bash
# 1. Run full test suite with verbose output
python run_tests.py --verbose

# 2. Validate configurations
taxglide validate --year 2025

# 3. Test a sample calculation
taxglide calc --year 2025 --income 80000

# 4. Only then proceed with your changes
```

### Test Accuracy

The test suite validates TaxGlide against **real Swiss tax calculations**:

| Income (CHF) | Federal Tax | SG+Comm Tax | Total Tax | TaxGlide Error |
|--------------|-------------|-------------|-----------|----------------|
| 32,000       | 129.35      | 2,770.20    | 2,899.55  | **0.00** CHF   |
| 60,000       | 671.35      | 8,125.90    | 8,797.25  | **0.07** CHF   |
| 90,000       | 2,028.00    | 14,826.90   | 16,854.90 | **0.01** CHF   |
| 120,000      | 4,254.35    | 21,638.65   | 25,893.00 | **0.55** CHF   |

✅ **Maximum error: 0.55 CHF** - Exceptional accuracy for Swiss tax calculations!

### Official Verification Sources

Here you can calculate as well, if you don't trust the program :D

**🏛️ Official Tax Calculator (St. Gallen)**  
[https://www.sg.ch/steuern-finanzen/steuern/steuerkalkulator/privatperson.sendCQForm.html](https://www.sg.ch/steuern-finanzen/steuern/steuerkalkulator/privatperson.sendCQForm.html)

**📋 Federal Tax Law (Article 36 - Tax Brackets)**  
[https://www.fedlex.admin.ch/eli/cc/1991/1184_1184_1184/de](https://www.fedlex.admin.ch/eli/cc/1991/1184_1184_1184/de)

**📋 St. Gallen Cantonal Tax Law (Article 50 - Tax Brackets)**  
[https://www.gesetzessammlung.sg.ch/app/de/texts_of_law/811.1](https://www.gesetzessammlung.sg.ch/app/de/texts_of_law/811.1)

These official sources provide the legal foundation for TaxGlide's calculations and allow independent verification of results.

---

## Quick Start

### GUI Application
1. **Launch the desktop app**: `npm run tauri dev` (from `gui/` directory)
2. **Navigate to Calculator** for basic tax calculations
3. **Use the Optimizer** to find optimal deduction amounts
4. **Try the Scanner** for interactive deduction analysis with sortable tables

### CLI Commands
Calculate taxes for 80,000 CHF income in 2025 (uses default location: St. Gallen):
```bash
taxglide calc --year 2025 --income 80000
```

Calculate with specific canton and municipality:
```bash
taxglide calc --year 2025 --income 80000 --canton st_gallen --municipality st_gallen_city
```

Calculate with different cantonal and Federal incomes:
```bash
taxglide calc --year 2025 --income-sg 78000 --income-fed 80000
```

Find optimal deduction up to 10,000 CHF:
```bash
taxglide optimize --year 2025 --income 80000 --max-deduction 10000
```

Optimize with specific canton and municipality:
```bash
taxglide optimize --year 2025 --income 80000 --max-deduction 10000 --canton st_gallen --municipality st_gallen_city
```

Optimize with separate incomes:
```bash
taxglide optimize --year 2025 --income-sg 78000 --income-fed 80000 --max-deduction 10000
```

## Configuration Structure

TaxGlide now uses a unified configuration structure that supports multiple cantons and municipalities:

```
configs/
├── 2025/
│   └── switzerland.yaml     # Complete Swiss tax configuration including:
│                           # - Federal tax brackets (single & married filing)
│                           # - All canton definitions with tax brackets
│                           # - Municipality definitions with multipliers
│                           # - Default canton/municipality settings
```

### Adding New Cantons/Municipalities
To add support for new locations, simply edit `switzerland.yaml`:
1. Add canton entry under `cantons` section with tax brackets
2. Add municipalities under the canton with their multipliers
3. No code changes required!
4. Use via CLI: `--canton new_canton --municipality new_municipality`

## Commands Reference

### `calc` - Basic Tax Calculation

Calculate total taxes with breakdown by component. Supports both single income and separate SG/Federal incomes.

```bash
# Single income (same for both SG and Federal)
taxglide calc --year 2025 --income 75000 [OPTIONS]

# Separate incomes (different SG and Federal taxable incomes)
taxglide calc --year 2025 --income-sg 73000 --income-fed 75000 [OPTIONS]
```

**Options:**
- `--income AMOUNT`: Single taxable income for both SG and Federal (CHF)
- `--income-sg AMOUNT`: Cantonal taxable income (CHF)
- `--income-fed AMOUNT`: Federal taxable income (CHF)
- `--canton CODE`: Canton to use (e.g., 'st_gallen') - defaults to st_gallen 🆕
- `--municipality CODE`: Municipality to use (e.g., 'st_gallen_city') - defaults to st_gallen_city 🆕
- `--filing-status STATUS`: Filing status - `single` (default) or `married_joint` 🆕
- `--pick CODE`: Include specific multiplier (e.g., `--pick FEUER` for fire service tax)
- `--skip CODE`: Exclude multiplier (e.g., `--skip CHURCH` to skip church tax)
- `--json`: Output as JSON instead of formatted display

**Examples:**
```bash
# Basic calculation with defaults (cantonal + communal)
taxglide calc --year 2025 --income 75000

# Specify canton and municipality explicitly
taxglide calc --year 2025 --income 75000 --canton st_gallen --municipality st_gallen_city

# Separate cantonal and Federal incomes (e.g., different deductions)
taxglide calc --year 2025 --income-sg 73000 --income-fed 75000

# Include fire service tax
taxglide calc --year 2025 --income 75000 --pick FEUER

# Separate incomes with custom multipliers and JSON output
taxglide calc --year 2025 --income-sg 68000 --income-fed 70000 --pick FEUER --json

# Custom multiplier combination
taxglide calc --year 2025 --income 120000 --pick FEUER --pick CHURCH

# Married joint filing (income splitting)
taxglide calc --year 2025 --income 120000 --filing-status married_joint
```

**Sample Output (Single Income):**
```json
{
  "income_sg": 75000,
  "income_fed": 75000,
  "income": 75000,
  "federal": 1149.55,
  "sg_simple": 4890.0,
  "sg_after_mult": 11881.7,
  "total": 13031.25,
  "avg_rate": 17.37,
  "marginal_total": 28.43,
  "marginal_federal_hundreds": 5.94,
  "picks": ["GEMEINDE", "KANTON"]
}
```

**Sample Output (Separate Incomes):**
```json
{
  "income_sg": 73000,
  "income_fed": 75000,
  "income": null,
  "federal": 1149.55,
  "sg_simple": 4567.8,
  "sg_after_mult": 11099.7,
  "total": 12249.25,
  "avg_rate": 16.33,
  "marginal_total": 27.84,
  "marginal_federal_hundreds": 5.94,
  "picks": ["GEMEINDE", "KANTON"]
}
```

---

### `optimize` - Smart Deduction Optimization

Find the optimal deduction amount to maximize return on investment (ROI). Supports both single income and separate SG/Federal incomes.

```bash
# Single income (deduction applies to both SG and Federal)
taxglide optimize --year 2025 --income 85000 --max-deduction 15000 [OPTIONS]

# Separate incomes (deduction applies equally to both)
taxglide optimize --year 2025 --income-sg 83000 --income-fed 85000 --max-deduction 15000 [OPTIONS]
```

**Options:**
- `--income AMOUNT`: Single taxable income for both SG and Federal (CHF)
- `--income-sg AMOUNT`: Cantonal taxable income (CHF)
- `--income-fed AMOUNT`: Federal taxable income (CHF)
- `--max-deduction AMOUNT`: Maximum deduction to explore (CHF)
- `--step SIZE`: Deduction increment in CHF (default: 100)
- `--tolerance-bp BP`: ROI tolerance in basis points for plateau detection (default: 10.0)
- `--pick/--skip CODE`: Same as calc command
- `--json`: JSON output

**Note**: Optimization assumes the deduction applies equally to both SG and Federal incomes.

**Examples:**
```bash
# Find optimal deduction up to 12,000 CHF (single income)
taxglide optimize --year 2025 --income 85000 --max-deduction 12000

# Separate incomes scenario (e.g., different deductions already applied)
taxglide optimize --year 2025 --income-sg 83000 --income-fed 85000 --max-deduction 10000

# Fine-grained search with 50 CHF steps
taxglide optimize --year 2025 --income 95000 --max-deduction 8000 --step 50

# Higher tolerance for broader plateau (50 basis points = 0.5%)
taxglide optimize --year 2025 --income-sg 98000 --income-fed 100000 --max-deduction 15000 --tolerance-bp 50
```

**Key Concepts:**
- **ROI (Return on Investment)**: Tax saved per CHF deducted
- **Plateau**: Range of deductions with near-optimal ROI (within tolerance)
- **Sweet Spot**: Recommended deduction at end of plateau (conservative optimum)

**Sample Output (Single Income):**
```json
{
  "base_total": 18450.0,
  "sweet_spot": {
    "deduction": 3600,
    "new_income": 81400.0,
    "total_tax_at_spot": 15234.5,
    "tax_saved_absolute": 3215.5,
    "tax_saved_percent": 17.4,
    "original_incomes": {
      "sg_income": 85000,
      "fed_income": 85000,
      "same_income_used": true
    },
    "explanation": "End of near-max ROI plateau: last CHF before ROI drops meaningfully."
  }
}
```

**Sample Output (Separate Incomes):**
```json
{
  "base_total": 17892.3,
  "sweet_spot": {
    "deduction": 3400,
    "new_income": 81600.0,
    "new_income_sg": 79600.0,
    "new_income_fed": 81600.0,
    "total_tax_at_spot": 14558.7,
    "tax_saved_absolute": 3333.6,
    "tax_saved_percent": 18.6,
    "original_incomes": {
      "sg_income": 83000,
      "fed_income": 85000,
      "same_income_used": false
    },
    "explanation": "End of near-max ROI plateau: last CHF before ROI drops meaningfully."
  }
}
```

---

### `scan` - Detailed Deduction Analysis

Generate comprehensive data table for all deduction amounts in a range. Supports both single income and separate SG/Federal incomes.

```bash
# Single income
taxglide scan --year 2025 --income 90000 --max-deduction 10000 [OPTIONS]

# Separate incomes
taxglide scan --year 2025 --income-sg 88000 --income-fed 90000 --max-deduction 10000 [OPTIONS]
```

**Options:**
- `--income AMOUNT`: Single taxable income for both SG and Federal (CHF)
- `--income-sg AMOUNT`: Cantonal taxable income (CHF)
- `--income-fed AMOUNT`: Federal taxable income (CHF)
- `--max-deduction AMOUNT`: Maximum deduction to explore (CHF)
- `--d-step SIZE`: Deduction increment (default: 100)
- `--out PATH`: Output CSV file (default: "scan.csv")
- `--json`: Print JSON instead of writing CSV
- `--include-local-marginal/--no-include-local-marginal`: Include marginal rate calculation

**Examples:**
```bash
# Scan every 100 CHF up to 8,000 CHF deduction (single income)
taxglide scan --year 2025 --income 85000 --max-deduction 8000

# Separate incomes scan with custom output file
taxglide scan --year 2025 --income-sg 83000 --income-fed 85000 --max-deduction 8000 --out separate_income_scan.csv

# Fine scan every 25 CHF, save to custom file
taxglide scan --year 2025 --income 75000 --max-deduction 5000 --d-step 25 --out detailed_scan.csv

# JSON output for further analysis
taxglide scan --year 2025 --income-sg 93000 --income-fed 95000 --max-deduction 12000 --json
```

**CSV Columns:**
- `deduction`: Amount deducted
- `new_income`: Income after deduction (max of SG/Federal for compatibility)
- `new_income_sg`: SG income after deduction (when using separate incomes)
- `new_income_fed`: Federal income after deduction (when using separate incomes)
- `total_tax`: Combined tax liability
- `saved`: Tax saved vs. no deduction
- `roi_percent`: Return on investment percentage
- `federal_from/to/per100`: Federal bracket information
- `local_marginal_percent`: Local marginal rate (Δ100 CHF)

---

### `plot` - Tax Curve Visualization

Generate visual plots of tax curves with optional optimization annotations.

```bash
taxglide plot --year 2025 --min 50000 --max 150000 [OPTIONS]
```

**Options:**
- `--step SIZE`: Income increment for plotting (default: 100)
- `--out PATH`: Output image file (default: "curve.png")
- `--annotate-sweet-spot`: Add optimization overlay
- `--opt-income AMOUNT`: Income for optimization annotation
- `--opt-max-deduction AMOUNT`: Max deduction for optimization
- `--opt-step SIZE`: Deduction step for optimization (default: 100)
- `--opt-tolerance-bp BP`: Tolerance for plateau detection (default: 10.0)

**Examples:**
```bash
# Basic tax curve from 40k to 120k CHF
taxglide plot --year 2025 --min 40000 --max 120000

# Annotated plot showing sweet spot for 85k income
taxglide plot --year 2025 --min 70000 --max 100000 \
  --annotate-sweet-spot \
  --opt-income 85000 \
  --opt-max-deduction 10000
```

The plot shows:
- **Tax curve**: Total tax vs. taxable income
- **Shaded area**: Income range corresponding to near-optimal deduction plateau
- **Vertical line + marker**: Sweet spot income after optimal deduction
- **Annotation**: Deduction amount and explanation

---

### `validate` - Configuration Validation

Verify that tax configuration files are valid and consistent.

```bash
taxglide validate --year 2025
```

**What it checks:**
- YAML file syntax and structure
- Tax bracket ordering and completeness  
- Multiplier code uniqueness
- Reasonable value ranges
- Segment continuity (no gaps or overlaps)

**Examples:**
```bash
# Validate 2025 tax configs
taxglide validate --year 2025

# Check if configs exist for 2026
taxglide validate --year 2026
```

---

### `compare-brackets` - Bracket Analysis

Show which tax brackets apply before and after a deduction. Supports both single income and separate SG/Federal incomes.

```bash
# Single income
taxglide compare-brackets --year 2025 --income 82000 [OPTIONS]

# Separate incomes
taxglide compare-brackets --year 2025 --income-sg 80000 --income-fed 82000 [OPTIONS]
```

**Options:**
- `--income AMOUNT`: Single taxable income for both SG and Federal (CHF)
- `--income-sg AMOUNT`: Cantonal taxable income (CHF)
- `--income-fed AMOUNT`: Federal taxable income (CHF)
- `--deduction AMOUNT`: Amount to deduct (default: 0)

**Examples:**
```bash
# Check current brackets for 82k income
taxglide compare-brackets --year 2025 --income 82000

# Separate incomes bracket analysis
taxglide compare-brackets --year 2025 --income-sg 80000 --income-fed 82000

# See bracket change with 3,500 CHF deduction  
taxglide compare-brackets --year 2025 --income-sg 80000 --income-fed 82000 --deduction 3500
```

**Sample Output (Separate Incomes):**
```json
{
  "original_sg_income": 80000,
  "original_fed_income": 82000,
  "adjusted_sg_income": 76500.0,
  "adjusted_fed_income": 78500.0,
  "deduction_amount": 3500,
  "federal_bracket_before": {
    "from": 82000, "to": 108800, "per100": 6.60
  },
  "federal_bracket_after": {
    "from": 76100, "to": 82000, "per100": 5.94  
  },
  "federal_bracket_changed": true,
  "sg_bracket_before": {
    "lower": 60200, "width": 38100, "rate_percent": 9.2
  },
  "sg_bracket_after": {
    "lower": 60200, "width": 38100, "rate_percent": 9.2
  },
  "sg_bracket_changed": false
}
```

## Separate Income Functionality 🆕

TaxGlide now supports different taxable incomes for cantonal and Federal taxes, which is common when:
- Different deductions apply to cantonal vs. federal taxes
- Income sources are treated differently by each tax system
- You want to model "what-if" scenarios with varying income splits

### When to Use Separate Incomes
```bash
# Traditional: Same income for both systems
taxglide calc --year 2025 --income 80000

# Modern: Different taxable incomes
taxglide calc --year 2025 --income-sg 78000 --income-fed 80000
```

**Key Benefits:**
- **Accurate modeling**: Reflects real-world tax situations where deductions differ
- **Enhanced output**: Shows separate new incomes after optimization
- **Better planning**: Optimize deductions when they apply differently to each system
- **Backward compatible**: Existing workflows continue unchanged

### Enhanced Output Example
When using separate incomes, optimization shows both resulting incomes:
```json
{
  "sweet_spot": {
    "deduction": 3000,
    "new_income_sg": 75000.0,    # SG income after deduction
    "new_income_fed": 77000.0,   # Federal income after deduction
    "new_income": 77000.0,       # Max (for compatibility)
    "original_incomes": {
      "sg_income": 78000,
      "fed_income": 80000,
      "same_income_used": false
    }
  }
}
```

---

## Married Joint Filing 🆕

TaxGlide supports Swiss married joint filing which uses income splitting for cantonal taxes and separate tax tables for federal taxes.

```bash
# Single filing (default)
taxglide calc --year 2025 --income 94000

# Married joint filing
taxglide calc --year 2025 --income 94000 --filing-status married_joint

# Works with all commands
taxglide optimize --year 2025 --income 94000 --max-deduction 10000 --filing-status married_joint
```

---

## Swiss Tax System Explained

### Federal Taxes
- **Marginal brackets**: Tax rate increases with income
- **100 CHF steps**: Rates apply to each complete 100 CHF block
- **Ceiling method**: Income rounded up to next 100 CHF for rate determination

### Cantonal Taxes (e.g., St. Gallen)
- **Progressive brackets**: Flat rate applied to portion of income in each bracket
- **High-income overrides**: Flat percentage above threshold where applicable (e.g., 8.5% above 264,200 CHF for SG)
- **Municipality-specific multipliers**: Cantonal and municipal rates are **additive factors** applied to base tax

### Multipliers (Municipality-Specific)
Example for St. Gallen city:
- `KANTON` (1.05): Cantonal multiplier - 105% of simple tax
- `GEMEINDE` (1.38): Municipal multiplier - 138% of simple tax  
- `FEUER` (0.14): Fire service - 14% of simple tax
- `CHURCH` (0.00): Church tax - varies by municipality/confession

**Total Cantonal Tax** = Simple Tax × (sum of selected multipliers)

## Understanding Optimization Results

### ROI (Return on Investment)
```
ROI = Tax Saved ÷ Deduction Amount
```
Example: Deducting 1,000 CHF saves 284 CHF in taxes → ROI = 28.4%

### Plateau Detection
The optimizer finds ranges where ROI stays near the maximum (within tolerance):
- **Narrow plateau**: Sharp tax bracket transitions
- **Wide plateau**: Gradual rate changes
- **Multiple peaks**: Complex bracket interactions

### Sweet Spot Selection
The algorithm recommends the **end of the plateau** (highest deduction with near-max ROI) because:
- **Conservative**: Maximizes deduction while maintaining high efficiency
- **Robust**: Less sensitive to small income changes
- **Practical**: Allows for income fluctuations

## Configuration Files

### Federal Configuration (`federal.yaml`)
```yaml
segments:
  - { from: 76100, to: 82000, at_income: 76100, base_tax_at: 1149.55, per100: 5.94 }
  - { from: 82000, to: 108800, at_income: 82000, base_tax_at: 1500.00, per100: 6.60 }
```

### Cantonal Configuration (within `switzerland.yaml`)
```yaml
cantons:
  st_gallen:
    name: "St. Gallen"
    abbreviation: "SG"
    brackets:
      - { lower: 60200, width: 38100, rate_percent: 9.2 }
      - { lower: 98300, width: 165900, rate_percent: 9.4 }
    override:
      flat_percent_above:
        threshold: 264200
        percent: 8.5
    municipalities:
      st_gallen_city:
        name: "St. Gallen"
        multipliers:
          canton: { name: "Kanton", code: "KANTON", rate: 1.05, default_selected: true }
          municipal: { name: "Gemeinde", code: "GEMEINDE", rate: 1.38, default_selected: true }
```

### Complete Configuration Structure
See the complete `switzerland.yaml` structure in `configs/2025/switzerland.yaml` which includes:
- Federal tax brackets for both single and married filing statuses
- Canton definitions with their tax brackets and rules
- Municipality definitions with their specific multipliers
- Default canton/municipality settings for backward compatibility

## Advanced Usage

### Batch Processing
```bash
# Optimize for multiple income levels
for income in 70000 80000 90000 100000; do
  echo "Income: $income"
  taxglide optimize --year 2025 --income $income --max-deduction 15000 --json
done
```

### Analysis Pipeline
```bash
# 1. Generate detailed scan data
taxglide scan --year 2025 --income 85000 --max-deduction 10000 --out analysis.csv

# 2. Find optimization results  
taxglide optimize --year 2025 --income 85000 --max-deduction 10000 --json > optimization.json

# 3. Create annotated visualization
taxglide plot --year 2025 --min 75000 --max 95000 \
  --annotate-sweet-spot --opt-income 85000 --opt-max-deduction 10000
```

## Tips & Best Practices

1. **Start with `calc`** to understand your current tax situation
2. **Use `optimize`** to find the sweet spot for deductions
3. **Use `scan`** for detailed analysis and external processing
4. **Check bracket transitions** with `compare-brackets` 
5. **Visualize** complex scenarios with annotated plots
6. **Always validate** configurations after updates

## Contributing

To add support for new cantons or municipalities:

1. Edit `configs/YEAR/switzerland.yaml` to add:
   - New canton entry under `cantons` section
   - Municipality entries under the canton with their multipliers
2. Run `taxglide validate --year YEAR` to verify configuration
3. Use new location: `taxglide calc --canton new_canton --municipality new_municipality`
4. No code changes required - the system automatically supports new locations!
