from .stgallen import simple_tax_sg
from .federal import tax_federal, federal_marginal_hundreds
from .multipliers import apply_multipliers, MultPick
from .optimize import optimize_deduction
from .models import (
    FederalConfig, StGallenConfig, MultipliersConfig,
    CalcResult, Breakdown 
)