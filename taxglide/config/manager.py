"""Configuration manager for Switzerland tax configurations.

Handles loading, modifying, and saving multi-canton configurations.
"""

from __future__ import annotations
import shutil
from pathlib import Path
from ruamel.yaml import YAML
from typing import Dict, Any, List, Optional
from datetime import datetime
import copy

from ..engine.models import (
    SwitzerlandConfig, Canton, Municipality, MunicipalityMultiplier,
    SgBracket, FederalConfig, FedSegment, FedRoundCfg, RoundCfg, SgOverride
)


class ConfigManager:
    """Manager for Switzerland tax configuration files."""
    
    def __init__(self, config_root: Path):
        """Initialize config manager.
        
        Args:
            config_root: Path to the configs directory
        """
        self.config_root = config_root
    
    def get_available_years(self) -> List[int]:
        """Get list of available tax years."""
        years = []
        if not self.config_root.exists():
            return years
            
        for item in self.config_root.iterdir():
            if item.is_dir() and item.name.isdigit():
                years.append(int(item.name))
        
        return sorted(years)
    
    def year_exists(self, year: int) -> bool:
        """Check if a tax year configuration exists."""
        year_dir = self.config_root / str(year)
        config_file = year_dir / "switzerland.yaml"
        return year_dir.exists() and config_file.exists()
    
    def create_year(self, source_year: int, target_year: int, overwrite: bool = False) -> Dict[str, Any]:
        """Create new year configuration by copying from existing year.
        
        Args:
            source_year: Year to copy from
            target_year: Year to create
            overwrite: Whether to overwrite if target exists
            
        Returns:
            Dict with operation result
        """
        source_dir = self.config_root / str(source_year)
        target_dir = self.config_root / str(target_year)
        
        if not source_dir.exists():
            raise ValueError(f"Source year {source_year} does not exist")
        
        if target_dir.exists() and not overwrite:
            raise ValueError(f"Target year {target_year} already exists. Use overwrite=True to replace.")
        
        # Remove target if it exists and overwrite is True
        if target_dir.exists() and overwrite:
            shutil.rmtree(target_dir)
        
        # Copy entire directory
        shutil.copytree(source_dir, target_dir)
        
        return {
            "source_year": source_year,
            "target_year": target_year,
            "success": True,
            "message": f"Successfully created {target_year} configuration from {source_year}"
        }
    
    def load_config(self, year: int) -> SwitzerlandConfig:
        """Load Switzerland configuration for a given year."""
        from ..io.loader import load_switzerland_config
        return load_switzerland_config(self.config_root, year)
    
    def save_config(self, year: int, config: SwitzerlandConfig) -> Dict[str, Any]:
        """Save Switzerland configuration to file.
        
        Always creates an archive copy of the existing file before overwriting.
        
        Args:
            year: Tax year
            config: Configuration to save
            
        Returns:
            Dict with save result
        """
        year_dir = self.config_root / str(year)
        config_file = year_dir / "switzerland.yaml"
        
        # Ensure directory exists
        year_dir.mkdir(parents=True, exist_ok=True)
        
        # Create archive directory
        archive_dir = year_dir / "_archive"
        archive_dir.mkdir(exist_ok=True)
        
        # Always create archive of existing file (if it exists)
        archive_file = None
        if config_file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_file = archive_dir / f"switzerland_{timestamp}.yaml"
            shutil.copy2(config_file, archive_file)
        
        try:
            # Convert Pydantic model to dict for YAML serialization
            config_dict = config.model_dump(by_alias=True, exclude_none=True)
            
            # Use ruamel.yaml for better formatting and potential comment preservation
            yaml_handler = YAML()
            yaml_handler.preserve_quotes = True
            yaml_handler.width = 150  # Wider to prevent wrapping of longer entries
            yaml_handler.indent(mapping=2, sequence=4, offset=2)
            yaml_handler.default_flow_style = None  # Use mixed flow/block style
            
            # Apply custom formatting for specific sections
            config_dict = self._apply_custom_formatting(config_dict)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                # Add header comment
                f.write("# Multi-Canton Swiss Tax Configuration\n")
                f.write("# This file defines tax rules for multiple cantons and their municipalities\n")
                f.write("\n")
                yaml_handler.dump(config_dict, f)
            
            return {
                "success": True,
                "message": f"Configuration saved successfully for year {year}",
                "archive_file": str(archive_file) if archive_file else None
            }
            
        except Exception as e:
            # Restore archive if save failed
            if archive_file and archive_file.exists():
                shutil.copy2(archive_file, config_file)
                # Keep archive file for audit trail - don't delete it
            
            raise ValueError(f"Failed to save configuration: {str(e)}")
    
    def get_config_summary(self, year: int) -> Dict[str, Any]:
        """Get summary of configuration for a year."""
        config = self.load_config(year)
        
        cantons_summary = []
        for canton_key, canton in config.cantons.items():
            municipalities = []
            for muni_key, muni in canton.municipalities.items():
                municipalities.append({
                    "key": muni_key,
                    "name": muni.name,
                    "multiplier_count": len(muni.multipliers)
                })
            
            cantons_summary.append({
                "key": canton_key,
                "name": canton.name,
                "abbreviation": canton.abbreviation,
                "bracket_count": len(canton.brackets),
                "municipality_count": len(canton.municipalities),
                "municipalities": municipalities
            })
        
        return {
            "year": year,
            "schema_version": config.schema_version,
            "country": config.country,
            "currency": config.currency,
            "canton_count": len(config.cantons),
            "cantons": cantons_summary,
            "defaults": config.defaults,
            "federal_filing_statuses": ["single", "married_joint"]
        }
    
    def create_canton(self, year: int, canton_key: str, canton_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new canton in configuration.
        
        Args:
            year: Tax year
            canton_key: Unique key for the canton
            canton_data: Canton configuration data
            
        Returns:
            Dict with operation result
        """
        config = self.load_config(year)
        
        if canton_key in config.cantons:
            raise ValueError(f"Canton '{canton_key}' already exists")
        
        # Validate and create canton
        canton = self._create_canton_from_data(canton_data)
        config.cantons[canton_key] = canton
        
        # Validate the entire config
        from ..io.loader import _validate_switzerland_config
        _validate_switzerland_config(config)
        
        # Save updated config
        save_result = self.save_config(year, config)
        
        return {
            "success": True,
            "canton_key": canton_key,
            "canton_name": canton.name,
            "message": f"Canton '{canton.name}' created successfully",
            "archive_file": save_result.get("archive_file")
        }
    
    def update_canton(self, year: int, canton_key: str, canton_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing canton in configuration."""
        config = self.load_config(year)
        
        if canton_key not in config.cantons:
            raise ValueError(f"Canton '{canton_key}' does not exist")
        
        # Update canton
        updated_canton = self._create_canton_from_data(canton_data)
        config.cantons[canton_key] = updated_canton
        
        # Validate the entire config
        from ..io.loader import _validate_switzerland_config
        _validate_switzerland_config(config)
        
        # Save updated config
        save_result = self.save_config(year, config)
        
        return {
            "success": True,
            "canton_key": canton_key,
            "canton_name": updated_canton.name,
            "message": f"Canton '{updated_canton.name}' updated successfully",
            "archive_file": save_result.get("archive_file")
        }
    
    def delete_canton(self, year: int, canton_key: str) -> Dict[str, Any]:
        """Delete canton from configuration."""
        config = self.load_config(year)
        
        if canton_key not in config.cantons:
            raise ValueError(f"Canton '{canton_key}' does not exist")
        
        if len(config.cantons) <= 1:
            raise ValueError("Cannot delete the last canton")
        
        canton_name = config.cantons[canton_key].name
        del config.cantons[canton_key]
        
        # Update defaults if necessary
        if config.defaults.get("canton") == canton_key:
            # Set to first remaining canton
            config.defaults["canton"] = next(iter(config.cantons.keys()))
            config.defaults["municipality"] = next(iter(config.cantons[config.defaults["canton"]].municipalities.keys()))
        
        # Save updated config
        save_result = self.save_config(year, config)
        
        return {
            "success": True,
            "canton_key": canton_key,
            "canton_name": canton_name,
            "message": f"Canton '{canton_name}' deleted successfully",
            "archive_file": save_result.get("archive_file")
        }
    
    def create_municipality(self, year: int, canton_key: str, municipality_key: str, municipality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new municipality in a canton."""
        config = self.load_config(year)
        
        if canton_key not in config.cantons:
            raise ValueError(f"Canton '{canton_key}' does not exist")
        
        canton = config.cantons[canton_key]
        
        if municipality_key in canton.municipalities:
            raise ValueError(f"Municipality '{municipality_key}' already exists in canton '{canton_key}'")
        
        # Create municipality
        municipality = self._create_municipality_from_data(municipality_data)
        canton.municipalities[municipality_key] = municipality
        
        # Validate the entire config
        from ..io.loader import _validate_switzerland_config
        _validate_switzerland_config(config)
        
        # Save updated config
        save_result = self.save_config(year, config)
        
        return {
            "success": True,
            "canton_key": canton_key,
            "municipality_key": municipality_key,
            "municipality_name": municipality.name,
            "message": f"Municipality '{municipality.name}' created successfully in canton '{canton.name}'",
            "archive_file": save_result.get("archive_file")
        }
    
    def update_municipality(self, year: int, canton_key: str, municipality_key: str, municipality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing municipality in a canton."""
        config = self.load_config(year)
        
        if canton_key not in config.cantons:
            raise ValueError(f"Canton '{canton_key}' does not exist")
        
        canton = config.cantons[canton_key]
        
        if municipality_key not in canton.municipalities:
            raise ValueError(f"Municipality '{municipality_key}' does not exist in canton '{canton_key}'")
        
        # Update municipality
        updated_municipality = self._create_municipality_from_data(municipality_data)
        canton.municipalities[municipality_key] = updated_municipality
        
        # Validate the entire config
        from ..io.loader import _validate_switzerland_config
        _validate_switzerland_config(config)
        
        # Save updated config
        save_result = self.save_config(year, config)
        
        return {
            "success": True,
            "canton_key": canton_key,
            "municipality_key": municipality_key,
            "municipality_name": updated_municipality.name,
            "message": f"Municipality '{updated_municipality.name}' updated successfully",
            "archive_file": save_result.get("archive_file")
        }
    
    def delete_municipality(self, year: int, canton_key: str, municipality_key: str) -> Dict[str, Any]:
        """Delete municipality from a canton."""
        config = self.load_config(year)
        
        if canton_key not in config.cantons:
            raise ValueError(f"Canton '{canton_key}' does not exist")
        
        canton = config.cantons[canton_key]
        
        if municipality_key not in canton.municipalities:
            raise ValueError(f"Municipality '{municipality_key}' does not exist in canton '{canton_key}'")
        
        if len(canton.municipalities) <= 1:
            raise ValueError("Cannot delete the last municipality in a canton")
        
        municipality_name = canton.municipalities[municipality_key].name
        del canton.municipalities[municipality_key]
        
        # Update defaults if necessary
        if (config.defaults.get("canton") == canton_key and 
            config.defaults.get("municipality") == municipality_key):
            # Set to first remaining municipality in this canton
            config.defaults["municipality"] = next(iter(canton.municipalities.keys()))
        
        # Save updated config
        save_result = self.save_config(year, config)
        
        return {
            "success": True,
            "canton_key": canton_key,
            "municipality_key": municipality_key,
            "municipality_name": municipality_name,
            "message": f"Municipality '{municipality_name}' deleted successfully",
            "archive_file": save_result.get("archive_file")
        }
    
    def update_federal_brackets(self, year: int, filing_status: str, segments_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update federal tax brackets for a filing status."""
        config = self.load_config(year)
        
        if filing_status not in ["single", "married_joint"]:
            raise ValueError(f"Invalid filing status: {filing_status}. Must be 'single' or 'married_joint'")
        
        # Create new segments
        segments = []
        for seg_data in segments_data:
            # Use model_validate to properly handle field aliases
            segment = FedSegment.model_validate(seg_data)
            segments.append(segment)
        
        # Update the federal config
        fed_config = getattr(config.federal, filing_status)
        fed_config.segments = segments
        
        # Validate the entire config
        from ..io.loader import _validate_switzerland_config
        _validate_switzerland_config(config)
        
        # Save updated config
        save_result = self.save_config(year, config)
        
        return {
            "success": True,
            "filing_status": filing_status,
            "segments_count": len(segments),
            "message": f"Federal brackets for '{filing_status}' updated successfully",
            "archive_file": save_result.get("archive_file")
        }
    
    def _create_canton_from_data(self, data: Dict[str, Any]) -> Canton:
        """Create Canton object from dictionary data."""
        # Parse brackets
        brackets = []
        for bracket_data in data.get("brackets", []):
            bracket = SgBracket(
                lower=bracket_data["lower"],
                width=bracket_data["width"],
                rate_percent=bracket_data["rate_percent"]
            )
            brackets.append(bracket)
        
        # Parse rounding config
        rounding_data = data.get("rounding", {})
        rounding = RoundCfg(
            taxable_step=rounding_data.get("taxable_step", 1),
            tax_round_to=rounding_data.get("tax_round_to", 0),
            scope=rounding_data.get("scope", "as_official")
        )
        
        # Parse override if present
        override = None
        if "override" in data and data["override"]:
            override = SgOverride(
                flat_percent_above=data["override"].get("flat_percent_above")
            )
        
        # Parse municipalities
        municipalities = {}
        for muni_key, muni_data in data.get("municipalities", {}).items():
            municipalities[muni_key] = self._create_municipality_from_data(muni_data)
        
        return Canton(
            name=data["name"],
            abbreviation=data["abbreviation"],
            model=data.get("model", "percent_of_bracket_portion"),
            rounding=rounding,
            brackets=brackets,
            override=override,
            notes=data.get("notes"),
            municipalities=municipalities
        )
    
    def _create_municipality_from_data(self, data: Dict[str, Any]) -> Municipality:
        """Create Municipality object from dictionary data."""
        # Parse multipliers
        multipliers = {}
        for mult_key, mult_data in data.get("multipliers", {}).items():
            multiplier = MunicipalityMultiplier(
                name=mult_data["name"],
                code=mult_data["code"],
                kind=mult_data.get("kind", "factor"),
                rate=mult_data["rate"],
                optional=mult_data.get("optional", False),
                default_selected=mult_data.get("default_selected", True)
            )
            multipliers[mult_key] = multiplier
        
        return Municipality(
            name=data["name"],
            multipliers=multipliers,
            multiplier_order=data.get("multiplier_order", [])
        )
    
    def _apply_custom_formatting(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Apply custom formatting to specific sections for better readability.
        
        This method formats federal tax segments and tax brackets in a more compact,
        readable inline flow style similar to the original format.
        """
        from ruamel.yaml.comments import CommentedMap, CommentedSeq
        
        # Convert to CommentedMap for better control
        formatted_config = CommentedMap(config_dict)
        
        # Add section comments
        if "federal" in formatted_config:
            formatted_config.yaml_set_comment_before_after_key(
                "federal", 
                before="\n# Federal tax configuration (same for all cantons, varies by filing status)"
            )
        
        if "cantons" in formatted_config:
            formatted_config.yaml_set_comment_before_after_key(
                "cantons", 
                before="\n# Canton definitions"
            )
        
        if "defaults" in formatted_config:
            formatted_config.yaml_set_comment_before_after_key(
                "defaults", 
                before="\n# Default canton and municipality for backward compatibility"
            )
        
        # Format federal segments with inline flow style
        if "federal" in formatted_config:
            federal = CommentedMap(formatted_config["federal"])
            
            for filing_status in ["single", "married_joint"]:
                if filing_status in federal:
                    filing_config = CommentedMap(federal[filing_status])
                    
                    if "segments" in filing_config:
                        segments = CommentedSeq(filing_config["segments"])
                        
                        # Format each segment as inline flow style
                        for i, segment in enumerate(segments):
                            segment_map = CommentedMap(segment)
                            segment_map.fa.set_flow_style()  # Force flow style (inline)
                            segments[i] = segment_map
                        
                        filing_config["segments"] = segments
                    
                    federal[filing_status] = filing_config
            
            formatted_config["federal"] = federal
        
        # Format canton brackets with inline flow style
        if "cantons" in formatted_config:
            cantons = CommentedMap(formatted_config["cantons"])
            
            for canton_key, canton_config in cantons.items():
                canton_map = CommentedMap(canton_config)
                
                if "brackets" in canton_map:
                    brackets = CommentedSeq(canton_map["brackets"])
                    
                    # Format each bracket as inline flow style
                    for i, bracket in enumerate(brackets):
                        bracket_map = CommentedMap(bracket)
                        bracket_map.fa.set_flow_style()  # Force flow style (inline)
                        brackets[i] = bracket_map
                    
                    canton_map["brackets"] = brackets
                
                cantons[canton_key] = canton_map
            
            formatted_config["cantons"] = cantons
        
        return formatted_config
