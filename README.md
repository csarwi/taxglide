# TaxGlide 🇨🇭

A comprehensive Swiss tax calculator and optimizer for **St. Gallen (SG) cantonal + Swiss federal taxes**. Built with configuration-driven tax models and advanced deduction optimization algorithms.

Almost mainly written with ChatGPT-5 and Claude.

## Features

- **Accurate Swiss Tax Models**: Federal (marginal brackets) + St. Gallen (progressive + multipliers)
- **Smart Deduction Optimization**: Find optimal deduction amounts using ROI analysis with plateau detection
- **Flexible Multiplier System**: Handle cantonal, communal, fire service, and church taxes
- **Rich CLI Interface**: Multiple commands for calculation, optimization, scanning, and visualization
- **Configuration-Driven**: Easy to update tax rules via YAML files
- **Export Capabilities**: JSON output and CSV scanning for analysis

## Installation

```bash
pip install -e .
```

## Quick Start

Calculate taxes for 80,000 CHF income in 2025:
```bash
taxglide calc --year 2025 --income 80000
```

Find optimal deduction up to 10,000 CHF:
```bash
taxglide optimize --year 2025 --income 80000 --max-deduction 10000
```

## Configuration Structure

```
configs/
├── 2025/
│   ├── federal.yaml      # Swiss federal tax brackets
│   ├── stgallen.yaml     # SG cantonal tax brackets  
│   └── multipliers.yaml  # Tax multipliers (cantonal, communal, etc.)
```

## Commands Reference

### `calc` - Basic Tax Calculation

Calculate total taxes with breakdown by component.

```bash
taxglide calc --year 2025 --income 75000 [OPTIONS]
```

**Options:**
- `--pick CODE`: Include specific multiplier (e.g., `--pick FEUER` for fire service tax)
- `--skip CODE`: Exclude multiplier (e.g., `--skip CHURCH` to skip church tax)
- `--json`: Output as JSON instead of formatted display

**Examples:**
```bash
# Basic calculation with defaults (cantonal + communal)
taxglide calc --year 2025 --income 75000

# Include fire service tax
taxglide calc --year 2025 --income 75000 --pick FEUER

# Exclude church tax and get JSON output
taxglide calc --year 2025 --income 75000 --skip CHURCH --json

# Custom multiplier combination
taxglide calc --year 2025 --income 120000 --pick FEUER --pick CHURCH
```

**Sample Output:**
```json
{
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

---

### `optimize` - Smart Deduction Optimization

Find the optimal deduction amount to maximize return on investment (ROI).

```bash
taxglide optimize --year 2025 --income 85000 --max-deduction 15000 [OPTIONS]
```

**Options:**
- `--step SIZE`: Deduction increment in CHF (default: 100)
- `--tolerance-bp BP`: ROI tolerance in basis points for plateau detection (default: 10.0)
- `--pick/--skip CODE`: Same as calc command
- `--json`: JSON output

**Examples:**
```bash
# Find optimal deduction up to 12,000 CHF
taxglide optimize --year 2025 --income 85000 --max-deduction 12000

# Fine-grained search with 50 CHF steps
taxglide optimize --year 2025 --income 95000 --max-deduction 8000 --step 50

# Higher tolerance for broader plateau (50 basis points = 0.5%)
taxglide optimize --year 2025 --income 100000 --max-deduction 15000 --tolerance-bp 50
```

**Key Concepts:**
- **ROI (Return on Investment)**: Tax saved per CHF deducted
- **Plateau**: Range of deductions with near-optimal ROI (within tolerance)
- **Sweet Spot**: Recommended deduction at end of plateau (conservative optimum)

**Sample Output:**
```json
{
  "base_total": 18450.0,
  "best_rate": {
    "deduction": 3400,
    "savings_rate_percent": 28.43
  },
  "plateau_near_max_roi": {
    "min_d": 3300,
    "max_d": 3600,
    "tolerance_bp": 10.0
  },
  "sweet_spot": {
    "deduction": 3600,
    "new_income": 81400.0,
    "explanation": "End of near-max ROI plateau: last CHF before ROI drops meaningfully."
  }
}
```

---

### `scan` - Detailed Deduction Analysis

Generate comprehensive data table for all deduction amounts in a range.

```bash
taxglide scan --year 2025 --income 90000 --max-deduction 10000 [OPTIONS]
```

**Options:**
- `--d-step SIZE`: Deduction increment (default: 100)
- `--out PATH`: Output CSV file (default: "scan.csv")
- `--json`: Print JSON instead of writing CSV
- `--include-local-marginal/--no-include-local-marginal`: Include marginal rate calculation

**Examples:**
```bash
# Scan every 100 CHF up to 8,000 CHF deduction
taxglide scan --year 2025 --income 85000 --max-deduction 8000

# Fine scan every 25 CHF, save to custom file
taxglide scan --year 2025 --income 75000 --max-deduction 5000 --d-step 25 --out detailed_scan.csv

# JSON output for further analysis
taxglide scan --year 2025 --income 95000 --max-deduction 12000 --json
```

**CSV Columns:**
- `deduction`: Amount deducted
- `new_income`: Income after deduction  
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

Show which tax brackets apply before and after a deduction.

```bash
taxglide compare-brackets --year 2025 --income 82000 [OPTIONS]
```

**Options:**
- `--deduction-amount AMOUNT`: Amount to deduct (default: 0)

**Examples:**
```bash
# Check current brackets for 82k income
taxglide compare-brackets --year 2025 --income 82000

# See bracket change with 3,500 CHF deduction  
taxglide compare-brackets --year 2025 --income 82000 --deduction-amount 3500
```

**Sample Output:**
```json
{
  "original_income": 82000,
  "adjusted_income": 78500.0,
  "federal_bracket_before": {
    "from": 82000, "to": 108800, "per100": 6.60
  },
  "federal_bracket_after": {
    "from": 76100, "to": 82000, "per100": 5.94  
  },
  "bracket_changed": true
}
```

## Swiss Tax System Explained

### Federal Taxes
- **Marginal brackets**: Tax rate increases with income
- **100 CHF steps**: Rates apply to each complete 100 CHF block
- **Ceiling method**: Income rounded up to next 100 CHF for rate determination

### St. Gallen Cantonal Taxes
- **Progressive brackets**: Flat rate applied to portion of income in each bracket
- **High-income override**: Flat percentage above threshold (currently 8.5% above 264,200 CHF)
- **Multiplier system**: Cantonal and communal rates are **additive factors** applied to base tax

### Multipliers (St. Gallen System)
- `KANTON` (1.05): Cantonal multiplier - 105% of simple tax
- `GEMEINDE` (1.38): Municipal multiplier - 138% of simple tax  
- `FEUER` (0.14): Fire service - 14% of simple tax
- `CHURCH` (0.00): Church tax - varies by municipality/confession

**Total SG Tax** = Simple Tax × (sum of selected multipliers)

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

### St. Gallen Configuration (`stgallen.yaml`)  
```yaml
brackets:
  - { lower: 60200, width: 38100, rate_percent: 9.2 }
  - { lower: 98300, width: 165900, rate_percent: 9.4 }
override:
  flat_percent_above:
    threshold: 264200
    percent: 8.5
```

### Multipliers Configuration (`multipliers.yaml`)
```yaml
items:
  - { name: "Kanton", code: "KANTON", rate: 1.05, default_selected: true }
  - { name: "Gemeinde", code: "GEMEINDE", rate: 1.38, default_selected: true }
  - { name: "Feuerwehr", code: "FEUER", rate: 0.14, default_selected: false }
```

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

To add support for new cantons or update tax rules:

1. Create new configuration files in `configs/YEAR/`
2. Update validation rules in `loader.py` if needed
3. Run `taxglide validate --year YEAR` to verify
4. Add tests for edge cases and known tax scenarios