from pathlib import Path
import yaml
from ..engine.models import (
    SwitzerlandConfig, Canton, Municipality, MultipliersConfig, MultItem,
    FederalConfig, StGallenConfig
)


def load_yaml(path: Path):
    """Load YAML file safely."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_switzerland_config(root: Path, year: int) -> SwitzerlandConfig:
    """Load the new multi-canton Switzerland configuration."""
    y = str(year)
    config_file = root / y / "switzerland.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Switzerland config not found: {config_file}")
    
    data = load_yaml(config_file)
    config = SwitzerlandConfig(**data)
    _validate_switzerland_config(config)
    return config


def get_canton_and_municipality_config(
    config: SwitzerlandConfig, 
    canton_key: str = None, 
    municipality_key: str = None
) -> tuple[Canton, Municipality]:
    """Extract canton and municipality configuration from Switzerland config."""
    # Use defaults if not specified
    if canton_key is None:
        canton_key = config.defaults["canton"]
    if municipality_key is None:
        municipality_key = config.defaults["municipality"]
    
    if canton_key not in config.cantons:
        available = list(config.cantons.keys())
        raise ValueError(f"Canton '{canton_key}' not found. Available: {available}")
    
    canton = config.cantons[canton_key]
    
    if municipality_key not in canton.municipalities:
        available = list(canton.municipalities.keys())
        raise ValueError(f"Municipality '{municipality_key}' not found in canton '{canton_key}'. Available: {available}")
    
    municipality = canton.municipalities[municipality_key]
    return canton, municipality


def create_legacy_multipliers_config(municipality: Municipality) -> MultipliersConfig:
    """Convert new municipality multipliers to legacy MultipliersConfig for backward compatibility."""
    items = []
    for key, mult in municipality.multipliers.items():
        item = MultItem(
            name=mult.name,
            code=mult.code,
            kind=mult.kind,
            rate=mult.rate,
            optional=getattr(mult, 'optional', False),
            default_selected=mult.default_selected
        )
        items.append(item)
    
    return MultipliersConfig(
        order=municipality.multiplier_order,
        items=items
    )


def _validate_switzerland_config(config: SwitzerlandConfig):
    """Validate the Switzerland configuration."""
    # Validate federal configurations for both filing statuses
    for filing_status in ["single", "married_joint"]:
        fed_config = getattr(config.federal, filing_status)
        _validate_federal_config(fed_config, filing_status)
    
    # Validate each canton
    for canton_key, canton in config.cantons.items():
        _validate_canton_config(canton, canton_key)


def _validate_federal_config(fed: FederalConfig, filing_status: str):
    """Validate federal tax configuration."""
    last_to = -1
    last_from = -1
    for idx, s in enumerate(fed.segments):
        if s.from_ < 0:
            raise ValueError(f"Federal {filing_status} segment {idx}: 'from' must be >= 0")
        if s.to is not None and s.to < s.from_:
            raise ValueError(f"Federal {filing_status} segment {idx}: 'to' must be >= 'from' or null")
        if s.at_income < s.from_:
            raise ValueError(f"Federal {filing_status} segment {idx}: 'at_income' must be >= 'from'")
        if s.per100 < 0 or s.base_tax_at < 0:
            raise ValueError(f"Federal {filing_status} segment {idx}: negative rate/base not allowed")
        if idx > 0 and s.from_ <= last_from:
            raise ValueError(f"Federal {filing_status} segments must be strictly increasing at 'from' (idx={idx})")
        if last_to is not None and last_to != -1 and s.from_ < last_to:
            raise ValueError(f"Federal {filing_status} segments overlap at idx={idx}")
        last_from = s.from_
        last_to = s.to if s.to is not None else 10**12
    
    # Check for gaps in federal segments
    for i in range(len(fed.segments) - 1):
        current_to = fed.segments[i].to
        next_from = fed.segments[i + 1].from_
        if current_to is not None and current_to != next_from:
            raise ValueError(f"Gap in federal {filing_status} segments: {current_to} -> {next_from}")


def _validate_canton_config(canton: Canton, canton_key: str):
    """Validate canton configuration."""
    # Validate canton brackets
    last_lower = -1
    for idx, b in enumerate(canton.brackets):
        if b.lower < 0:
            raise ValueError(f"Canton {canton_key} bracket {idx}: lower must be >= 0")
        if b.width <= 0:
            raise ValueError(f"Canton {canton_key} bracket {idx}: width must be > 0")
        if b.rate_percent < 0:
            raise ValueError(f"Canton {canton_key} bracket {idx}: rate_percent must be >= 0")
        if b.lower <= last_lower:
            raise ValueError(f"Canton {canton_key} brackets must be strictly increasing by 'lower' (idx={idx})")
        last_lower = b.lower
    
    # Validate canton override if present
    if canton.override and canton.override.flat_percent_above:
        thr = int(canton.override.flat_percent_above.get("threshold", 0))
        pct = float(canton.override.flat_percent_above.get("percent", 0))
        if thr < 0 or pct < 0:
            raise ValueError(f"Canton {canton_key} override: threshold/percent must be non-negative")
    
    # Verify canton brackets are contiguous
    for i in range(len(canton.brackets) - 1):
        current_end = canton.brackets[i].lower + canton.brackets[i].width
        next_start = canton.brackets[i + 1].lower
        if current_end != next_start:
            raise ValueError(f"Gap in canton {canton_key} brackets: {current_end} -> {next_start}")
    
    # Validate each municipality in the canton
    for muni_key, municipality in canton.municipalities.items():
        _validate_municipality_config(municipality, canton_key, muni_key)


def _validate_municipality_config(municipality: Municipality, canton_key: str, muni_key: str):
    """Validate municipality configuration."""
    # Validate multipliers
    seen_codes = set()
    for mult_key, mult in municipality.multipliers.items():
        if mult.code in seen_codes:
            raise ValueError(f"Duplicate multiplier code '{mult.code}' in {canton_key}/{muni_key}")
        seen_codes.add(mult.code)
        
        if mult.rate < 0:
            raise ValueError(f"Multiplier rate must be non-negative: {mult.code} in {canton_key}/{muni_key}")
    
    # Validate multiplier order references existing multipliers
    for order_name in municipality.multiplier_order:
        if order_name not in [mult.name for mult in municipality.multipliers.values()]:
            available = [mult.name for mult in municipality.multipliers.values()]
            raise ValueError(f"Multiplier order references unknown multiplier '{order_name}' in {canton_key}/{muni_key}. Available: {available}")
    
    # Validate total default multiplier rate is reasonable
    total_default = sum(mult.rate for mult in municipality.multipliers.values() if mult.default_selected)
    if total_default > 5.0:  # 500% seems excessive
        raise ValueError(f"Default multipliers sum to {total_default:.2f} in {canton_key}/{muni_key} - seems too high")


