
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, getcontext
from typing import List, Optional, Literal, Dict, Union
from pydantic import BaseModel, Field, field_validator, ConfigDict

getcontext().prec = 28

CHF = Decimal

class RoundCfg(BaseModel):
    taxable_step: int = 1
    tax_round_to: int = 0  # 0=CHF 1; 5=nearest 5, etc.
    scope: Literal["as_official", "final_only", "per_component_then_final"] = "as_official"

class SgBracket(BaseModel):
    lower: int
    width: int
    rate_percent: float

class SgOverride(BaseModel):
    flat_percent_above: Optional[Dict[str, float]] = None  # {threshold, percent}

class StGallenConfig(BaseModel):
    currency: Literal["CHF"]
    model: Literal["percent_of_bracket_portion"] = "percent_of_bracket_portion"
    rounding: RoundCfg
    brackets: List[SgBracket]
    override: Optional[SgOverride] = None

class FedSegment(BaseModel):
    from_: int = Field(alias="from")
    to: Optional[int] = None
    at_income: int
    base_tax_at: float
    per100: float

class FedRoundCfg(BaseModel):
    model_config = ConfigDict(extra="forbid")
    per_100_step: bool = True
    step_size: int = 100
    step_mode: Literal["ceil", "floor"] = "ceil"

class FederalConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    currency: Literal["CHF"]
    rounding: FedRoundCfg
    segments: List[FedSegment]
    notes: Optional[str] = None

# Multi-canton support models
class MunicipalityMultiplier(BaseModel):
    name: str
    code: str
    kind: Literal["factor"] = "factor"
    rate: float
    optional: bool = False
    default_selected: bool = True

class Municipality(BaseModel):
    name: str
    multipliers: Dict[str, MunicipalityMultiplier]
    multiplier_order: List[str]

class Canton(BaseModel):
    name: str
    abbreviation: str
    model: Literal["percent_of_bracket_portion"] = "percent_of_bracket_portion"
    rounding: RoundCfg
    brackets: List[SgBracket]
    override: Optional[SgOverride] = None
    notes: Optional[str] = None
    municipalities: Dict[str, Municipality]

class FederalByFilingStatus(BaseModel):
    single: FederalConfig
    married_joint: FederalConfig

class SwitzerlandConfig(BaseModel):
    schema_version: str
    currency: Literal["CHF"]
    country: Literal["Switzerland"]
    federal: FederalByFilingStatus
    cantons: Dict[str, Canton]
    defaults: Dict[str, str]

# Legacy models kept for backward compatibility with existing code
class MultItem(BaseModel):
    name: str
    code: str
    kind: Literal["factor"] = "factor"
    rate: float
    exclusive_group: Optional[str] = None
    optional: bool = False
    default_selected: bool = True

class MultipliersConfig(BaseModel):
    order: List[str]
    items: List[MultItem]

@dataclass
class Breakdown:
    federal: CHF
    sg_simple: CHF
    sg_after_mult: CHF
    combined: CHF

# Filing status enumeration
FilingStatus = Literal["single", "married_joint"]

@dataclass
class CalcResult:
    income: CHF
    federal: CHF
    sg_simple: CHF
    sg_after_mult: CHF
    total: CHF
    avg_rate: float
    marginal_total: float
    marginal_federal_hundreds: float
    picks: List[str]
    filing_status: Optional[FilingStatus] = "single"

# helpers

def chf(x: float | int | Decimal) -> CHF:
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))

def round_to_increment(amount: CHF, inc: int) -> CHF:
    if inc <= 0:
        return amount
    q = Decimal(inc)
    # nearest multiple of inc, half up
    return (amount / q).to_integral_value(rounding=ROUND_HALF_UP) * q