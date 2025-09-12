
from decimal import Decimal
from pathlib import Path
from taxglide.io.loader import load_configs
from taxglide.engine.stgallen import simple_tax_sg
from taxglide.engine.federal import tax_federal
from taxglide.engine.multipliers import apply_multipliers, MultPick

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "configs"

def test_placeholder():
    sg, fed, mult = load_configs(CONFIG_ROOT, 2025)
    income = Decimal(150000)
    sg_simple = simple_tax_sg(income, sg)
    assert sg_simple >= 0
    fed_tax = tax_federal(income, fed)
    assert fed_tax >= 0
    total_sg = apply_multipliers(sg_simple, mult, MultPick(["KANTON","GEMEINDE","FEUER"]))
    assert total_sg >= sg_simple