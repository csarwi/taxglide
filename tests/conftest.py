"""Common test fixtures and configuration for TaxGlide tests."""

import pytest
from pathlib import Path
from decimal import Decimal

from taxglide.io.loader import load_configs, load_configs_with_filing_status
from taxglide.engine.models import chf

# Path to test configs (use the actual 2025 configs for now)
CONFIG_ROOT = Path(__file__).resolve().parents[1] / "configs"

@pytest.fixture
def config_root():
    """Path to configuration files."""
    return CONFIG_ROOT

@pytest.fixture
def year_2025():
    """Tax year for testing."""
    return 2025

@pytest.fixture
def configs_2025(config_root):
    """Load 2025 tax configurations."""
    sg_cfg, fed_cfg, mult_cfg = load_configs(config_root, 2025)
    return sg_cfg, fed_cfg, mult_cfg

@pytest.fixture
def configs_2025_married(config_root):
    """Load 2025 tax configurations for married joint filing."""
    sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(config_root, 2025, "married_joint")
    return sg_cfg, fed_cfg, mult_cfg

@pytest.fixture
def configs_2025_single(config_root):
    """Load 2025 tax configurations for single filing."""
    sg_cfg, fed_cfg, mult_cfg = load_configs_with_filing_status(config_root, 2025, "single")
    return sg_cfg, fed_cfg, mult_cfg

@pytest.fixture
def default_multiplier_codes(configs_2025):
    """Get default multiplier codes for 2025."""
    _, _, mult_cfg = configs_2025
    return sorted([item.code for item in mult_cfg.items if item.default_selected])

class TaxTestCase:
    """Test case data structure for tax calculations."""
    def __init__(self, income: int, federal_tax: float, sg_simple: float, 
                 sg_after_mult: float, total_tax: float, description: str = ""):
        self.income = income
        self.federal_tax = chf(federal_tax)
        self.sg_simple = chf(sg_simple)
        self.sg_after_mult = chf(sg_after_mult) 
        self.total_tax = chf(total_tax)
        self.description = description
        
    def __repr__(self):
        return f"TaxTestCase(income={self.income}, total={self.total_tax})"


class SeparateIncomeTaxTestCase:
    """Test case data structure for separate SG and Federal income calculations."""
    def __init__(self, sg_income: int, fed_income: int, federal_tax: float, 
                 sg_simple: float, sg_after_mult: float, total_tax: float, 
                 description: str = ""):
        self.sg_income = sg_income
        self.fed_income = fed_income
        self.federal_tax = chf(federal_tax)
        self.sg_simple = chf(sg_simple)
        self.sg_after_mult = chf(sg_after_mult)
        self.total_tax = chf(total_tax)
        self.description = description
        
    def __repr__(self):
        return f"SeparateIncomeTaxTestCase(sg={self.sg_income}, fed={self.fed_income}, total={self.total_tax})"

@pytest.fixture
def sample_tax_cases():
    """Real Swiss tax test cases from official calculations."""
    return [
        TaxTestCase(
            income=32000,
            federal_tax=129.35,
            sg_simple=1140.00,
            sg_after_mult=2770.20,
            total_tax=2899.55,
            description="Lower income - basic brackets"
        ),
        TaxTestCase(
            income=60000,
            federal_tax=671.35,
            sg_simple=3343.99,
            sg_after_mult=8125.90,
            total_tax=8797.25,
            description="Mid income - federal taxable range"
        ),
        TaxTestCase(
            income=90000,
            federal_tax=2028.00,
            sg_simple=6101.60,
            sg_after_mult=14826.90,
            total_tax=16854.90,
            description="Higher income - progressive brackets"
        ),
        TaxTestCase(
            income=120000,
            federal_tax=4254.35,
            sg_simple=8904.79,
            sg_after_mult=21638.65,
            total_tax=25893.00,
            description="High income - higher marginal rates"
        )
    ]


@pytest.fixture
def separate_income_test_cases():
    """Real Swiss tax cases with different SG and Federal taxable incomes.
    
    These cases demonstrate scenarios where cantonal and federal deductions differ,
    resulting in different taxable income bases for SG vs Federal calculations.
    """
    return [
        SeparateIncomeTaxTestCase(
            sg_income=130000,
            fed_income=110000,
            federal_tax=3374.40,
            sg_simple=9843.86,  # 23922.85 / 2.43
            sg_after_mult=23922.85,
            total_tax=27297.25,  # 23922.85 + 3374.40
            description="High income - significant federal deduction advantage (20k difference)"
        ),
        SeparateIncomeTaxTestCase(
            sg_income=94700,
            fed_income=91700,
            federal_tax=2140.15,
            sg_simple=6535.06,  # 15877.60 / 2.43
            sg_after_mult=15877.60,
            total_tax=18017.75,  # 15877.60 + 2140.15
            description="Mid-high income - moderate federal deduction advantage (3k difference)"
        ),
        SeparateIncomeTaxTestCase(
            sg_income=35000,
            fed_income=32000,
            federal_tax=129.35,
            sg_simple=1343.99,  # 3265.90 / 2.43
            sg_after_mult=3265.90,
            total_tax=3395.25,  # 3265.90 + 129.35
            description="Lower income - small federal deduction advantage (3k difference)"
        )
    ]
