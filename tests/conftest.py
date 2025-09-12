"""Common test fixtures and configuration for TaxGlide tests."""

import pytest
from pathlib import Path
from decimal import Decimal

from taxglide.io.loader import load_configs
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
