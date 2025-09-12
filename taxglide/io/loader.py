
from pathlib import Path
import yaml
from ..engine.models import FederalConfig, StGallenConfig, MultipliersConfig

def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_configs(root: Path, year: int):
    y = str(year)
    sg = StGallenConfig(**load_yaml(root / y / "stgallen.yaml"))
    fed = FederalConfig(**load_yaml(root / y / "federal.yaml"))
    mult = MultipliersConfig(**load_yaml(root / y / "multipliers.yaml"))
    return sg, fed, mult