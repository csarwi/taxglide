# TaxGlide CLI ↔ GUI Contract Specification

This document defines the interface contract between the TaxGlide CLI and GUI applications, based on comprehensive analysis of the existing codebase.

## Version & Compatibility

### Schema Versioning
- **Current Schema Version**: `1.0` (to be implemented)
- **TaxGlide Version**: `0.3.0` (from pyproject.toml)
- **Version Command**: `taxglide version --json --schema-version` (to be implemented)
- **Compatibility**: GUI must validate schema version matches expected range before proceeding

### Version Commands (To Be Implemented)
```bash
# Human-readable version info
taxglide version

# Machine-readable version with schema
taxglide version --json --schema-version
```

**Proposed Version JSON Response**:
```json
{
  "success": true,
  "schema_version": "1.0",
  "timestamp": "2025-09-15T10:30:00Z",
  "data": {
    "version": "0.3.0",
    "schema_version": "1.0",
    "build_date": "2025-09-15T10:30:00Z",
    "platform": "windows"
  }
}
```

## Command Table

| Command | Purpose | Key Arguments | Current JSON Support | Output Format |
|---------|---------|---------------|---------------------|---------------|
| `calc` | Calculate tax scenarios | `--json`, `--income` OR `--income-sg --income-fed`, `--filing-status` | ✅ Full | Tax calculation results |
| `optimize` | Find optimal tax strategies | `--json`, `--income` OR `--income-sg --income-fed`, `--max-deduction` | ✅ Full | Optimization recommendations |
| `scan` | Scan deduction ranges | `--json`, `--income` OR `--income-sg --income-fed`, `--max-deduction`, `--d-step` | ✅ Full | Deduction scan results |
| `compare-brackets` | Compare tax brackets | `--income` OR `--income-sg --income-fed`, `--deduction` | ❌ No JSON | Bracket comparison |
| `validate` | Validate config files | `--year` | ❌ No JSON | Validation results |
| `version` | Show version info | `--json`, `--schema-version` | ❌ Not implemented | Version information |

## Success Response Formats

### Response Envelope (To Be Implemented)
For consistency, all JSON responses should follow this envelope:
```json
{
  "success": true,
  "schema_version": "1.0",
  "timestamp": "2025-09-15T10:30:00Z",
  "data": { /* command-specific data */ }
}
```

**Current Implementation**: Commands return data directly (no envelope). We need to add the envelope wrapper.

### Calculate Command
**Command**: `taxglide calc --json --income-sg 78000 --income-fed 80000`

**Current Response**:
```json
{
  "income_sg": 78000,
  "income_fed": 80000,
  "income": null,
  "federal": 1381.2,
  "sg_simple": 4997.6,
  "sg_after_mult": 12144.168,
  "total": 13525.368,
  "avg_rate": 0.1690671,
  "marginal_total": 0.22356,
  "marginal_federal_hundreds": 0.0595,
  "picks": ["GEMEINDE", "KANTON"],
  "filing_status": "single",
  "feuer_warning": "⚠️ Missing FEUER tax: +700 CHF (add --pick FEUER)"
}
```

**Key Fields**:
- `income_sg`, `income_fed`: Separate incomes (primary use case)
- `income`: Single income (null when using separate incomes)
- `federal`, `sg_simple`, `sg_after_mult`, `total`: Tax components
- `avg_rate`, `marginal_total`: Tax rates (decimals, not percentages)
- `picks`: Applied multiplier codes
- `filing_status`: "single" or "married_joint"
- `feuer_warning`: Optional warning about missing fire service tax

### Optimize Command
**Command**: `taxglide optimize --json --income-sg 78000 --income-fed 80000 --max-deduction 8000`

**Current Response Structure**:
```json
{
  "base_total": 13525.368,
  "best_rate": {
    "deduction": 100,
    "new_income": 79900.0,
    "total": 13497.062,
    "saved": 28.306,
    "savings_rate": 0.28306,
    "savings_rate_percent": 28.306
  },
  "plateau_near_max_roi": {
    "min_d": 100,
    "max_d": 3900,
    "roi_min_percent": 28.295,
    "roi_max_percent": 28.306,
    "tolerance_bp": 5.4
  },
  "sweet_spot": {
    "deduction": 3900,
    "new_income": 76100.0,
    "total_tax_at_spot": 12421.834,
    "tax_saved_absolute": 1103.534,
    "tax_saved_percent": 8.159,
    "federal_tax_at_spot": 1149.55,
    "sg_tax_at_spot": 11272.284,
    "baseline": {
      "total_tax": 13525.368,
      "federal_tax": 1381.2,
      "sg_tax": 12144.168
    },
    "explanation": "End of near-max ROI plateau: last CHF before ROI drops meaningfully.",
    "income_details": {
      "original_sg": 78000,
      "original_fed": 80000,
      "after_deduction_sg": 74100.0,
      "after_deduction_fed": 76100.0
    },
    "multipliers": {
      "applied": ["GEMEINDE", "KANTON"],
      "total_rate": 2.43,
      "feuer_warning": "⚠️ Missing FEUER tax: +649 CHF (add --pick FEUER)"
    },
    "optimization_summary": {
      "roi_percent": 28.296,
      "plateau_width_chf": 3800,
      "federal_bracket_changed": true,
      "marginal_rate_percent": 25.306
    }
  },
  "federal_100_nudge": {
    "nudge_chf": 1,
    "estimated_federal_saving": 5.95
  },
  "adaptive_retry_used": {
    "original_tolerance_bp": 18.0,
    "chosen_tolerance_bp": 5.4,
    "roi_improvement": 0.144,
    "utilization_improvement": -0.025,
    "selection_reason": "balanced_improvement"
  },
  "multipliers_applied": ["GEMEINDE", "KANTON"],
  "tolerance_info": {
    "tolerance_used_bp": 18.0,
    "tolerance_percent": 0.18,
    "tolerance_source": "auto-selected",
    "explanation": "..."
  }
}
```

**Key Features**:
- Comprehensive optimization data with sweet spot recommendations
- Separate income support with `income_details`
- Adaptive retry mechanism for better utilization
- Detailed ROI plateau analysis
- Federal bracket change detection

### Scan Command
**Command**: `taxglide scan --json --income-sg 78000 --income-fed 80000 --max-deduction 2000 --d-step 500`

**Current Response** (Array of objects):
```json
[
  {
    "deduction": 0,
    "new_income": 80000.0,
    "total_tax": 13525.368,
    "saved": 0.0,
    "roi_percent": 0.0,
    "sg_simple": 4997.6,
    "sg_after_multipliers": 12144.168,
    "federal": 1381.2,
    "federal_from": 76100,
    "federal_to": 82000,
    "federal_per100": 5.94,
    "local_marginal_percent": 28.306,
    "new_income_sg": 78000.0,
    "new_income_fed": 80000.0
  }
]
```

**Key Features**:
- Dense table format for analysis
- Separate income tracking with `new_income_sg`, `new_income_fed`
- Federal bracket information for each deduction level
- Local marginal rates computed via finite differences

### Compare Brackets Command (Needs JSON Support)
**Command**: `taxglide compare-brackets --income-sg 78000 --income-fed 80000 --deduction 5000`

**Current Response** (Non-JSON):
```python
{
    'original_sg_income': 78000,
    'original_fed_income': 80000,
    'adjusted_sg_income': 75000.0,
    'adjusted_fed_income': 75000.0,
    'deduction_amount': 5000,
    'federal_bracket_before': {'from': 76100, 'to': 82000, 'per100': 5.94, 'at_income': 76100},
    'federal_bracket_after': {'from': 58000, 'to': 76100, 'per100': 2.97, 'at_income': 58000},
    'federal_bracket_changed': True,
    'sg_bracket_before': {'lower': 60200, 'upper': 98300, 'rate_percent': 9.2},
    'sg_bracket_after': {'lower': 60200, 'upper': 98300, 'rate_percent': 9.2},
    'sg_bracket_changed': False
}
```

**Needed**: Add `--json` flag support for this command.

### Validate Command (Needs JSON Support)
**Command**: `taxglide validate --year 2025`

**Current Response** (Non-JSON):
```python
{'status': 'valid', 'year': 2025, 'message': 'All configurations valid'}
```

**Needed**: Add `--json` flag support for this command.

## Error Response Format

### Proposed Error JSON Structure
```json
{
  "success": false,
  "schema_version": "1.0",
  "timestamp": "2025-09-15T10:30:00Z",
  "error": {
    "code": "INVALID_INPUT",
    "message": "Must provide either --income, or both --income-sg and --income-fed.",
    "details": {
      "field": "income_parameters",
      "provided_value": null,
      "expected": "income OR (income_sg AND income_fed)"
    }
  }
}
```

### Error Codes
| Code | Description | Exit Code | Current CLI Behavior |
|------|-------------|-----------|---------------------|
| `INVALID_INPUT` | Invalid command arguments | 2 | ✅ Implemented |
| `CALCULATION_ERROR` | Error during tax calculation | 3 | ❌ Needs mapping |
| `FILE_NOT_FOUND` | Config files missing | 4 | ❌ Needs mapping |
| `VALIDATION_ERROR` | Config validation failed | 5 | ❌ Needs mapping |
| `INTERNAL_ERROR` | Unexpected internal error | 8 | ❌ Needs mapping |
| `SCHEMA_MISMATCH` | Incompatible schema version | 9 | ❌ Needs implementation |

## Exit Code Map

| Exit Code | Meaning | GUI Action | Current Implementation |
|-----------|---------|------------|----------------------|
| 0 | Success | Parse JSON response | ✅ Working |
| 1 | General error | Show generic error message | ✅ Used by validate |
| 2 | Invalid input | Show validation error to user | ✅ Used for param validation |
| 3+ | Other errors | Show specific error messages | ❌ Need to implement |

## Data Formats & Standards

### Number Formats (Current Implementation)
- **Currency**: Always as decimal numbers (e.g., `13525.368`)
- **Percentages**: 
  - Rate fields: decimal ratios (e.g., `0.1690671` for 16.91%)
  - Percent fields: actual percentages (e.g., `28.296` for 28.296%)
- **Integers**: For deductions, incomes, years

### String Formats
- **Filing Status**: lowercase with underscores (`single`, `married_joint`)
- **Multiplier Codes**: uppercase (`KANTON`, `GEMEINDE`, `FEUER`)

### Key Income Parameters
The CLI supports two income models:
1. **Single Income**: `--income 80000` (both SG and Federal use same amount)
2. **Separate Incomes**: `--income-sg 78000 --income-fed 80000` (different amounts)

**Response Fields**:
- `income`: Single income value (null when using separate incomes)
- `income_sg`, `income_fed`: Always present, show actual incomes used

## Implementation Gaps & Required Changes

### 1. Add Version Command
```bash
# Need to implement
taxglide version [--json] [--schema-version]
```

### 2. Add JSON Support to Missing Commands
- `compare-brackets --json`
- `validate --json`

### 3. Add Response Envelope
Wrap all JSON responses in success/error envelope with schema version and timestamp.

### 4. Add Schema Version Validation
- Include `schema_version` in all responses
- Validate compatibility in GUI

### 5. Standardize Error Handling
- Map Python exceptions to specific error codes
- Return JSON errors with proper structure when `--json` flag is used

### 6. Number Format Consistency
- Document the percentage format distinction
- Consider standardizing to always use decimal ratios

## GUI Integration Notes

### Process Execution
- **Command**: Execute `taxglide.exe` (not through shell)
- **Arguments**: Always use long-form flags (`--income-sg` not `-i`)
- **Working Directory**: Same directory as GUI executable
- **Timeout**: 30 seconds for calc/optimize, 60 seconds for scan
- **Cancellation**: Process termination (no graceful cancellation)

### Primary Use Case
The GUI will primarily use separate income parameters:
- `--income-sg 78000 --income-fed 80000` (most common)
- `--income 80000` (simplified case)

### Key Workflow
1. **Version Check**: `taxglide version --json --schema-version`
2. **Calculate**: `taxglide calc --json --income-sg X --income-fed Y`
3. **Optimize**: `taxglide optimize --json --income-sg X --income-fed Y --max-deduction Z`
4. **Scan**: `taxglide scan --json --income-sg X --income-fed Y --max-deduction Z --d-step W`

### Performance Expectations (Current)
- `calc`: < 1 second ✅
- `optimize`: < 5 seconds ✅
- `scan`: < 30 seconds ✅
- `validate`: < 1 second ✅

## Backward Compatibility

The existing CLI JSON output is production-ready and should be preserved. All new features (version command, error envelopes, etc.) should be additive rather than breaking changes.
