"""Tests for configuration loading and validation."""

import pytest
from pathlib import Path
from decimal import Decimal
import tempfile
import yaml

from taxglide.io.loader import load_switzerland_config
from taxglide.engine.models import FederalConfig, StGallenConfig, MultipliersConfig


class TestConfigurationLoading:
    """Test configuration file loading using new multi-canton system."""
    
    def test_load_existing_configs(self, config_root, year_2025):
        """Test loading existing 2025 configurations."""
        config = load_switzerland_config(config_root, year_2025)
        
        # Verify basic structure
        assert config.currency == "CHF"
        assert len(config.cantons) > 0
        assert "st_gallen" in config.cantons
        assert len(config.cantons["st_gallen"].municipalities) > 0
        assert config.federal.single is not None
        assert config.federal.married_joint is not None
        assert len(config.federal.single.segments) > 0
        assert len(config.federal.married_joint.segments) > 0
    
    def test_load_nonexistent_year(self, config_root):
        """Test loading configurations for nonexistent year."""
        with pytest.raises((FileNotFoundError, OSError)):
            load_switzerland_config(config_root, 9999)  # Year that doesn't exist
