from pathlib import Path
import yaml
from ..engine.models import FederalConfig, StGallenConfig, MultipliersConfig


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_configs(sg: StGallenConfig, fed: FederalConfig, mult: MultipliersConfig):
    # --- Federal segments: ordered, non-overlapping, valid rates ---
    last_to = -1
    last_from = -1
    for idx, s in enumerate(fed.segments):
        if s.from_ < 0:
            raise ValueError(f"Federal segment {idx}: 'from' must be >= 0")
        if s.to is not None and s.to < s.from_:
            raise ValueError(f"Federal segment {idx}: 'to' must be >= 'from' or null")
        if s.at_income < s.from_:
            raise ValueError(f"Federal segment {idx}: 'at_income' must be >= 'from'")
        if s.per100 < 0 or s.base_tax_at < 0:
            raise ValueError(f"Federal segment {idx}: negative rate/base not allowed")
        if idx > 0 and s.from_ <= last_from:
            raise ValueError(f"Federal segments must be strictly increasing at 'from' (idx={idx})")
        if last_to is not None and last_to != -1 and s.from_ < last_to:
            raise ValueError(f"Federal segments overlap at idx={idx}")
        last_from = s.from_
        last_to = s.to if s.to is not None else 10**12

    # --- SG brackets: increasing lowers, positive widths, sane rates ---
    last_lower = -1
    for idx, b in enumerate(sg.brackets):
        if b.lower < 0:
            raise ValueError(f"SG bracket {idx}: lower must be >= 0")
        if b.width <= 0:
            raise ValueError(f"SG bracket {idx}: width must be > 0")
        if b.rate_percent < 0:
            raise ValueError(f"SG bracket {idx}: rate_percent must be >= 0")
        if b.lower <= last_lower:
            raise ValueError(f"SG brackets must be strictly increasing by 'lower' (idx={idx})")
        last_lower = b.lower
    if sg.override and sg.override.flat_percent_above:
        thr = int(sg.override.flat_percent_above.get("threshold", 0))
        pct = float(sg.override.flat_percent_above.get("percent", 0))
        if thr < 0 or pct < 0:
            raise ValueError("SG override: threshold/percent must be non-negative")

    # --- Multipliers: non-negative rates, unique codes ---
    seen = set()
    for it in mult.items:
        if it.code in seen:
            raise ValueError(f"Multiplier codes must be unique: {it.code}")
        seen.add(it.code)
        if it.rate < 0:
            raise ValueError(f"Multiplier rate must be non-negative: {it.code}")


    # Additional checks:
    
    # 1. Reasonable income ranges
    max_fed_income = fed.segments[-1].to if fed.segments[-1].to else 1_000_000
    max_sg_income = sg.brackets[-1].lower + sg.brackets[-1].width
    
    if max_fed_income < 100_000:
        raise ValueError(f"Federal config seems incomplete - max income only {max_fed_income}")
    
    # 2. SG brackets should cover reasonable range
    if max_sg_income < 50_000:
        raise ValueError(f"SG brackets may be incomplete - max coverage only {max_sg_income}")
    
    # 3. Multiplier sanity - total shouldn't exceed reasonable bounds
    total_multiplier = sum(item.rate for item in mult.items if item.default_selected)
    if total_multiplier > 5.0:  # 500% seems excessive
        raise ValueError(f"Default multipliers sum to {total_multiplier:.2f} - seems too high")
    
    # 4. Check for gaps in federal segments
    for i in range(len(fed.segments) - 1):
        current_to = fed.segments[i].to
        next_from = fed.segments[i + 1].from_
        if current_to is not None and current_to != next_from:
            raise ValueError(f"Gap in federal segments: {current_to} -> {next_from}")
    
    # 5. Verify SG brackets are contiguous
    for i in range(len(sg.brackets) - 1):
        current_end = sg.brackets[i].lower + sg.brackets[i].width
        next_start = sg.brackets[i + 1].lower
        if current_end != next_start:
            raise ValueError(f"Gap in SG brackets: {current_end} -> {next_start}")


def load_configs(root: Path, year: int):
    y = str(year)
    sg = StGallenConfig(**load_yaml(root / y / "stgallen.yaml"))
    fed = FederalConfig(**load_yaml(root / y / "federal.yaml"))
    mult = MultipliersConfig(**load_yaml(root / y / "multipliers.yaml"))
    _validate_configs(sg, fed, mult)
    return sg, fed, mult

def load_configs_with_filing_status(root: Path, year: int, filing_status: str = "single"):
    """Load configs with appropriate federal table based on filing status"""
    y = str(year)
    sg = StGallenConfig(**load_yaml(root / y / "stgallen.yaml"))
    
    # Load appropriate federal config based on filing status
    if filing_status == "married_joint":
        fed_file = root / y / "federal_married.yaml"
        if not fed_file.exists():
            # Fallback to regular federal config if married config doesn't exist
            fed_file = root / y / "federal.yaml"
    else:
        fed_file = root / y / "federal.yaml"
        
    fed = FederalConfig(**load_yaml(fed_file))
    mult = MultipliersConfig(**load_yaml(root / y / "multipliers.yaml"))
    _validate_configs(sg, fed, mult)
    return sg, fed, mult
