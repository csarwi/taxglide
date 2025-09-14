# Married Joint Filing Implementation

This document explains how the married joint filing feature implements Swiss tax law point 3.

## Swiss Tax Law Point 3

> "Für gemeinsam steuerpflichtige Ehegatten wird der Steuersatz des halben steuerbaren Einkommens angewendet."

Translation: "For jointly taxable spouses, the tax rate of half the taxable income is applied."

## How It Works

### Income Splitting Method

1. **Take the combined taxable income** (e.g., 120,000 CHF)
2. **Calculate the tax rate at half that income** (60,000 CHF)
3. **Apply that rate to the full income** (120,000 CHF)

This prevents married couples from being pushed into higher tax brackets unfairly.

### Example

Let's say the tax brackets are:
- 0-50,000 CHF: 5%
- 50,001-100,000 CHF: 10%
- 100,001+ CHF: 15%

**Single Person with 120,000 CHF:**
- First 50,000 × 5% = 2,500
- Next 50,000 × 10% = 5,000  
- Last 20,000 × 15% = 3,000
- **Total: 10,500 CHF**

**Married Couple with 120,000 CHF (using income splitting):**
- Tax rate at 60,000 CHF = (50,000 × 5% + 10,000 × 10%) / 60,000 = 5.83%
- Applied to full 120,000 CHF = 120,000 × 5.83% = **7,000 CHF**

**Savings: 3,500 CHF**

## Usage Examples

### CLI Usage

```bash
# Single filing (default)
python main.py calc --year 2025 --income 120000

# Married joint filing
python main.py calc --year 2025 --income 120000 --filing-status married_joint

# With separate SG and Federal incomes
python main.py calc --year 2025 --income-sg 118000 --income-fed 120000 --filing-status married_joint
```

### Comparison

```bash
# Compare single vs married joint at same income level
python main.py calc --year 2025 --income 120000 --filing-status single --json
python main.py calc --year 2025 --income 120000 --filing-status married_joint --json
```

## Implementation Notes

- The income splitting applies to **both** SG simple tax and Federal tax calculations
- Multipliers (like FEUER) are applied after the income splitting calculation
- All existing features (optimization, scanning, plotting) work with both filing statuses
- The feature is backward compatible - existing commands default to "single" filing

## Testing

Run the test script to see the difference:

```bash
python test_married_joint.py
```

This will show side-by-side comparisons of single vs married joint filing at different income levels.
