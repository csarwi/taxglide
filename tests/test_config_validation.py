"""Tests for configuration loading and validation."""

import pytest
from pathlib import Path
from decimal import Decimal
import tempfile
import yaml

from taxglide.io.loader import load_configs, _validate_configs
from taxglide.engine.models import FederalConfig, StGallenConfig, MultipliersConfig


class TestConfigurationLoading:
    """Test configuration file loading."""
    
    def test_load_existing_configs(self, config_root, year_2025):
        """Test loading existing 2025 configurations."""
        sg_cfg, fed_cfg, mult_cfg = load_configs(config_root, year_2025)
        
        # Verify types
        assert isinstance(sg_cfg, StGallenConfig)
        assert isinstance(fed_cfg, FederalConfig)
        assert isinstance(mult_cfg, MultipliersConfig)
        
        # Basic structural checks
        assert sg_cfg.currency == "CHF"
        assert fed_cfg.currency == "CHF"
        assert len(sg_cfg.brackets) > 0
        assert len(fed_cfg.segments) > 0
        assert len(mult_cfg.items) > 0
    
    def test_load_nonexistent_year(self, config_root):
        """Test loading configurations for nonexistent year."""
        with pytest.raises((FileNotFoundError, OSError)):
            load_configs(config_root, 9999)  # Year that doesn't exist


class TestConfigurationValidation:
    """Test configuration validation rules."""
    
    def create_temp_configs(self, sg_data, fed_data, mult_data):
        """Helper to create temporary config files."""
        temp_dir = Path(tempfile.mkdtemp())
        year_dir = temp_dir / "2025"
        year_dir.mkdir()
        
        (year_dir / "stgallen.yaml").write_text(yaml.dump(sg_data))
        (year_dir / "federal.yaml").write_text(yaml.dump(fed_data))
        (year_dir / "multipliers.yaml").write_text(yaml.dump(mult_data))
        
        return temp_dir
    
    def test_valid_configuration(self, configs_2025):
        """Test that current 2025 configs pass validation."""
        sg_cfg, fed_cfg, mult_cfg = configs_2025
        # Should not raise any exception
        _validate_configs(sg_cfg, fed_cfg, mult_cfg)
    
    def test_federal_segments_validation(self):
        """Test federal segments validation rules."""
        # Valid federal config
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [
                {"from": 0, "to": 50000, "at_income": 0, "base_tax_at": 0.0, "per100": 0.0},
                {"from": 50000, "to": 200000, "at_income": 50000, "base_tax_at": 1000.0, "per100": 1.0}
            ]
        }
        
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [{"lower": 0, "width": 100000, "rate_percent": 10.0}]
        }
        
        mult_data = {
            "order": ["TEST"], 
            "items": [{"name": "Test", "code": "TEST", "kind": "factor", "rate": 1.0, "default_selected": True}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        sg_cfg, fed_cfg, mult_cfg = load_configs(temp_dir, 2025)
        
        # Should pass validation
        _validate_configs(sg_cfg, fed_cfg, mult_cfg)
    
    def test_federal_segments_negative_rate(self):
        """Test federal segments with negative rates should fail."""
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [
                {"from": 0, "to": 200000, "at_income": 0, "base_tax_at": 0.0, "per100": -1.0}  # Negative rate
            ]
        }
        
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [{"lower": 0, "width": 100000, "rate_percent": 10.0}]
        }
        
        mult_data = {
            "order": ["TEST"], 
            "items": [{"name": "Test", "code": "TEST", "kind": "factor", "rate": 1.0, "default_selected": True}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        
        with pytest.raises(ValueError, match="negative rate"):
            load_configs(temp_dir, 2025)
    
    def test_federal_segments_overlapping(self):
        """Test overlapping federal segments should fail."""
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [
                {"from": 0, "to": 150000, "at_income": 0, "base_tax_at": 0.0, "per100": 0.0},
                {"from": 100000, "to": 200000, "at_income": 100000, "base_tax_at": 10000.0, "per100": 1.0}  # Overlaps with previous
            ]
        }
        
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [{"lower": 0, "width": 100000, "rate_percent": 10.0}]
        }
        
        mult_data = {
            "order": ["TEST"], 
            "items": [{"name": "Test", "code": "TEST", "kind": "factor", "rate": 1.0, "default_selected": True}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        
        with pytest.raises(ValueError, match="overlap"):
            load_configs(temp_dir, 2025)
    
    def test_sg_brackets_validation(self):
        """Test SG bracket validation rules."""
        # Test negative width
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [{"lower": 0, "width": -1000, "rate_percent": 10.0}]  # Negative width
        }
        
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [{"from": 0, "to": 200000, "at_income": 0, "base_tax_at": 0.0, "per100": 0.0}]
        }
        
        mult_data = {
            "order": ["TEST"], 
            "items": [{"name": "Test", "code": "TEST", "kind": "factor", "rate": 1.0, "default_selected": True}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        
        with pytest.raises(ValueError, match="width must be > 0"):
            load_configs(temp_dir, 2025)
    
    def test_sg_brackets_non_increasing(self):
        """Test non-increasing SG brackets should fail."""
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [
                {"lower": 1000, "width": 1000, "rate_percent": 5.0},
                {"lower": 500, "width": 1000, "rate_percent": 10.0}  # Lower than previous
            ]
        }
        
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [{"from": 0, "to": 200000, "at_income": 0, "base_tax_at": 0.0, "per100": 0.0}]
        }
        
        mult_data = {
            "order": ["TEST"], 
            "items": [{"name": "Test", "code": "TEST", "kind": "factor", "rate": 1.0, "default_selected": True}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        
        with pytest.raises(ValueError, match="strictly increasing"):
            load_configs(temp_dir, 2025)
    
    def test_multiplier_duplicate_codes(self):
        """Test duplicate multiplier codes should fail."""
        mult_data = {
            "order": ["TEST1", "TEST2"], 
            "items": [
                {"name": "Test1", "code": "DUPE", "kind": "factor", "rate": 1.0, "default_selected": True},
                {"name": "Test2", "code": "DUPE", "kind": "factor", "rate": 2.0, "default_selected": False}  # Duplicate code
            ]
        }
        
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [{"lower": 0, "width": 100000, "rate_percent": 10.0}]
        }
        
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [{"from": 0, "to": 200000, "at_income": 0, "base_tax_at": 0.0, "per100": 0.0}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        
        with pytest.raises(ValueError, match="codes must be unique"):
            load_configs(temp_dir, 2025)
    
    def test_multiplier_negative_rate(self):
        """Test negative multiplier rates should fail."""
        mult_data = {
            "order": ["TEST"], 
            "items": [{"name": "Test", "code": "TEST", "kind": "factor", "rate": -1.0, "default_selected": True}]  # Negative rate
        }
        
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [{"lower": 0, "width": 100000, "rate_percent": 10.0}]
        }
        
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [{"from": 0, "to": 200000, "at_income": 0, "base_tax_at": 0.0, "per100": 0.0}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        
        with pytest.raises(ValueError, match="rate must be non-negative"):
            load_configs(temp_dir, 2025)
    
    def test_reasonable_income_ranges(self):
        """Test validation of reasonable income ranges."""
        # Test with very low maximum income coverage
        fed_data = {
            "currency": "CHF",
            "rounding": {"per_100_step": True, "step_size": 100, "step_mode": "floor", "tax_round_to": 0, "scope": "as_official"},
            "segments": [{"from": 0, "to": 1000, "at_income": 0, "base_tax_at": 0.0, "per100": 0.0}]  # Only covers up to 1000 CHF
        }
        
        sg_data = {
            "currency": "CHF", "model": "percent_of_bracket_portion",
            "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
            "brackets": [{"lower": 0, "width": 1000, "rate_percent": 10.0}]  # Only covers up to 1000 CHF
        }
        
        mult_data = {
            "order": ["TEST"], 
            "items": [{"name": "Test", "code": "TEST", "kind": "factor", "rate": 1.0, "default_selected": True}]
        }
        
        temp_dir = self.create_temp_configs(sg_data, fed_data, mult_data)
        
        with pytest.raises(ValueError, match="seems incomplete"):
            load_configs(temp_dir, 2025)
