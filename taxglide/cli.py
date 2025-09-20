from __future__ import annotations
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import csv
import typer
from rich import print as rprint
import sys
import platform
from datetime import datetime, timezone

from .io.loader import load_switzerland_config, get_canton_and_municipality_config
from .engine.stgallen import simple_tax_sg, sg_bracket_info, simple_tax_sg_with_filing_status
from .engine.federal import (
    tax_federal,
    federal_marginal_hundreds,
    federal_segment_info,
    tax_federal_with_filing_status,
)
from .engine.multipliers import apply_multipliers, MultPick
from .engine.models import chf, FilingStatus
from .engine.optimize import optimize_deduction, optimize_deduction_adaptive, validate_optimization_inputs
from .viz.curve import plot_curve
from .config.manager import ConfigManager

app = typer.Typer(help="Swiss tax CLI (SG + Federal), config driven")

CONFIG_ROOT = Path(__file__).parent / "configs"

VALID_FILING_STATUSES = {"single", "married_joint"}

SCHEMA_VERSION = "1.0"
TAXGLIDE_VERSION = "0.4.1"  # Should match pyproject.toml

# Error codes for JSON responses
ERROR_CODES = {
    "INVALID_INPUT": 2,
    "CALCULATION_ERROR": 3,
    "FILE_NOT_FOUND": 4,
    "VALIDATION_ERROR": 5,
    "INTERNAL_ERROR": 8,
    "SCHEMA_MISMATCH": 9,
}

def _create_console_with_imports():
    """Create Rich console with all required imports."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    
    return Console(), Panel, Text, Table


def _create_json_response(data: Any, success: bool = True) -> Dict[str, Any]:
    """Create standardized JSON response envelope.
    
    Args:
        data: The response data to wrap
        success: Whether this is a success response
        
    Returns:
        Dict with standardized response envelope
    """
    return {
        "success": success,
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data
    }


def _create_json_error(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create standardized JSON error response.
    
    Args:
        code: Error code from ERROR_CODES
        message: Human-readable error message
        details: Optional additional error details
        
    Returns:
        Dict with standardized error response
    """
    error_data = {
        "code": code,
        "message": message
    }
    if details:
        error_data["details"] = details
        
    return {
        "success": False,
        "schema_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": error_data
    }


def _handle_json_error(error: Exception, json_mode: bool = False) -> None:
    """Handle exceptions and output appropriate error format.
    
    Args:
        error: The exception that occurred
        json_mode: Whether to output JSON error format
    """
    if isinstance(error, ValueError):
        if json_mode:
            error_response = _create_json_error("INVALID_INPUT", str(error))
            print(json.dumps(error_response, indent=2))
        else:
            rprint({"error": str(error)})
        raise typer.Exit(code=ERROR_CODES["INVALID_INPUT"])
    elif isinstance(error, FileNotFoundError):
        if json_mode:
            error_response = _create_json_error("FILE_NOT_FOUND", str(error))
            print(json.dumps(error_response, indent=2))
        else:
            rprint({"error": str(error)})
        raise typer.Exit(code=ERROR_CODES["FILE_NOT_FOUND"])
    else:
        if json_mode:
            error_response = _create_json_error("INTERNAL_ERROR", f"Unexpected error: {str(error)}")
            print(json.dumps(error_response, indent=2))
        else:
            rprint({"error": str(error)})
        raise typer.Exit(code=ERROR_CODES["INTERNAL_ERROR"])


def _print_multiplier_info(console, Text, multiplier_codes: List[str], mult_cfg, sg_simple: float = None):
    """Print multiplier information with factor calculation.
    
    Args:
        console: Rich console instance
        Text: Rich Text class
        multiplier_codes: List of applied multiplier codes  
        mult_cfg: Multipliers configuration
        sg_simple: SG simple tax amount (for factor calculation)
    """
    if multiplier_codes:
        from decimal import Decimal
        mult_text = Text()
        mult_text.append(f"📎 Applied Multipliers: {', '.join(multiplier_codes)}\n", style="cyan")
        
        # Calculate total factor
        total_rate = float(sum(Decimal(str(item.rate)) for item in mult_cfg.items if item.code in multiplier_codes))
        mult_text.append(f"Total Factor: ×{total_rate:.2f}  (={total_rate*100:.0f}% of SG simple)")
        console.print("\n", mult_text)


def _print_feuer_warning_if_present(text_obj, feuer_warning: str):
    """Add FEUER warning to a Rich Text object if present."""
    if feuer_warning:
        text_obj.append(f"\n\n{feuer_warning}", style="yellow")


def _validate_filing_status(value: str) -> str:
    """Validate filing status parameter.
    
    Args:
        value: Filing status string
        
    Returns:
        Validated filing status
        
    Raises:
        typer.BadParameter: If filing status is invalid
    """
    value = value.strip().lower()
    if value not in VALID_FILING_STATUSES:
        raise typer.BadParameter(
            f"Filing status must be one of: {', '.join(sorted(VALID_FILING_STATUSES))}"
        )
    return value


def _load_configs_new_style(year: int, canton_key: str = None, municipality_key: str = None, filing_status: str = "single"):
    """Load configuration using new multi-canton approach."""
    config = load_switzerland_config(CONFIG_ROOT, year)
    canton, municipality = get_canton_and_municipality_config(config, canton_key, municipality_key)
    
    # Get the appropriate federal config based on filing status
    fed_config = getattr(config.federal, filing_status)
    
    return config, canton, municipality, fed_config


def _get_adaptive_tolerance_bp(income: int) -> float:
    """Return income-adaptive tolerance in basis points.
    
    Very conservative tolerances to target 25-40% average utilization for practical
    multi-year tax planning. Prevents ROI plateaus from spanning entire deduction space.
    """
    if income < 25000:
        return 8.0    # 0.08% - very precise for low incomes
    elif income < 50000:
        return 12.0   # 0.12% - conservative for mid-income (addresses 34K issue) 
    elif income < 80000:
        return 15.0   # 0.15% - still conservative for higher mid-income
    elif income < 150000:
        return 18.0   # 0.18% - conservative for high income
    else:
        return 20.0   # 0.20% - prevent excessive utilization


def _print_optimization_result(result: dict, tolerance_bp: float, tolerance_source: str, base_income: int, max_deduction: int = None):
    """Print a comprehensive, user-friendly optimization result."""
    console, Panel, Text, Table = _create_console_with_imports()
    
    sweet_spot = result.get("sweet_spot")
    if not sweet_spot:
        console.print("❌ No optimization result found", style="red")
        return
    
    # Core recommendation
    deduction = sweet_spot["deduction"]
    tax_saved = sweet_spot["tax_saved_absolute"]
    roi = sweet_spot["optimization_summary"]["roi_percent"]
    new_income = sweet_spot["new_income"]
    
    # Create main result panel
    result_text = Text()
    result_text.append("💰 OPTIMAL DEDUCTION RECOMMENDATION\n\n", style="bold green")
    result_text.append(f"Deduct: {deduction:,} CHF\n", style="bold cyan")
    result_text.append(f"Tax savings: {tax_saved:,.0f} CHF\n", style="bold yellow")
    result_text.append(f"Return on investment: {roi:.1f}%\n", style="bold magenta")
    result_text.append(f"New taxable income: {new_income:,.0f} CHF", style="dim")
    
    # Add FEUER warning if present
    multipliers = sweet_spot.get("multipliers", {})
    feuer_warning = multipliers.get("feuer_warning")
    _print_feuer_warning_if_present(result_text, feuer_warning)
    
    # Add utilization warning if present
    utilization_warning = sweet_spot.get("utilization_warning")
    if utilization_warning:
        result_text.append(f"\n\n{utilization_warning['message']}", style="yellow")
    
    console.print(Panel(result_text, title="TaxGlide Optimization", border_style="green"))
    
    # Detailed tax breakdown
    baseline = sweet_spot.get("baseline", {})
    if baseline:
        tax_table = Table(title="📊 Tax Breakdown", show_header=True, header_style="bold blue")
        tax_table.add_column("Component", style="cyan")
        tax_table.add_column("Before Deduction", justify="right", style="red")
        tax_table.add_column("After Deduction", justify="right", style="green")
        tax_table.add_column("Savings", justify="right", style="yellow")
        
        fed_before = baseline.get("federal_tax", 0)
        fed_after = sweet_spot.get("federal_tax_at_spot", 0)
        fed_savings = fed_before - fed_after
        
        sg_before = baseline.get("sg_tax", 0)
        sg_after = sweet_spot.get("sg_tax_at_spot", 0)
        sg_savings = sg_before - sg_after
        
        total_before = baseline.get("total_tax", 0)
        total_after = sweet_spot.get("total_tax_at_spot", 0)
        
        tax_table.add_row("Federal Tax", f"{fed_before:,.0f} CHF", f"{fed_after:,.0f} CHF", f"{fed_savings:,.0f} CHF")
        tax_table.add_row("SG Tax", f"{sg_before:,.0f} CHF", f"{sg_after:,.0f} CHF", f"{sg_savings:,.0f} CHF")
        tax_table.add_row("[bold]Total Tax", f"[bold]{total_before:,.0f} CHF", f"[bold]{total_after:,.0f} CHF", f"[bold]{tax_saved:,.0f} CHF")
        
        console.print("\n", tax_table)
    
    # Optimization details panel
    opt_summary = sweet_spot.get("optimization_summary", {})
    details_text = Text()
    details_text.append("🎯 OPTIMIZATION DETAILS\n\n", style="bold blue")
    details_text.append(f"Strategy: {sweet_spot.get('explanation', 'N/A')}\n", style="italic")
    
    if opt_summary:
        plateau_width = opt_summary.get("plateau_width_chf", 0)
        marginal_rate = opt_summary.get("marginal_rate_percent", 0)
        bracket_changed = opt_summary.get("federal_bracket_changed", False)
        
        details_text.append(f"ROI Plateau: {plateau_width:,} CHF wide\n")
        details_text.append(f"Marginal Tax Rate: {marginal_rate:.1f}%\n")
        details_text.append(f"Federal Bracket Change: {'Yes' if bracket_changed else 'No'}\n")
        if max_deduction:
            details_text.append(f"Utilization: {deduction / max_deduction:.1%} of max deduction\n")
    
    # Add tolerance info
    details_text.append(f"\nTolerance: {tolerance_bp:.0f} basis points ({tolerance_source})")
    
    console.print(Panel(details_text, title="Technical Analysis", border_style="blue"))
    
    # Adaptive retry information
    adaptive_info = result.get("adaptive_retry_used")
    retry_info = result.get("adaptive_retry_info")
    if adaptive_info and retry_info:
        retry_text = Text()
        retry_text.append("🔄 ADAPTIVE OPTIMIZATION APPLIED\n\n", style="bold magenta")
        retry_text.append(f"Reason: Low utilization detected ({retry_info['triggered_due_to_low_utilization']:.1%} < {retry_info['utilization_threshold']:.0%} threshold)\n")
        retry_text.append(f"Selected: {adaptive_info['chosen_tolerance_bp']:.0f}bp tolerance ({adaptive_info['selection_reason'].replace('_', ' ')})\n")
        retry_text.append(f"ROI change: {adaptive_info['roi_improvement']:+.1f}%\n")
        retry_text.append(f"Utilization change: {adaptive_info['utilization_improvement']:+.1%}")
        
        console.print("\n", Panel(retry_text, title="Adaptive Enhancement", border_style="magenta"))
        
        # Show alternative results table
        if retry_info.get("retry_results_tested"):
            alt_table = Table(title="Alternative Tolerance Results", show_header=True, header_style="bold magenta")
            alt_table.add_column("Tolerance (bp)", justify="center")
            alt_table.add_column("Deduction", justify="right")
            alt_table.add_column("Tax Saved", justify="right")
            alt_table.add_column("ROI", justify="right")
            alt_table.add_column("Utilization", justify="right")
            
            # Add initial result
            initial = retry_info["initial_result"]
            alt_table.add_row(
                f"{initial['tolerance_bp']:.0f}",
                f"{initial['deduction']:,} CHF",
                "N/A",
                f"{initial['roi_percent']:.1f}%", 
                f"{initial['utilization_ratio']:.1%}",
                style="dim"
            )
            
            # Add retry results
            for retry in retry_info["retry_results_tested"]:
                style = "bold green" if retry["tolerance_bp"] == adaptive_info["chosen_tolerance_bp"] else None
                alt_table.add_row(
                    f"{retry['tolerance_bp']:.0f}",
                    f"{retry['deduction']:,} CHF",
                    f"{retry['tax_saved']:,.0f} CHF",
                    f"{retry['roi_percent']:.1f}%",
                    f"{retry['utilization_ratio']:.1%}",
                    style=style
                )
            
            console.print("\n", alt_table)
    
    # Multipliers applied - use shared function
    if multipliers.get("applied"):
        # We need to get mult_cfg to calculate the factor properly
        # For now, use the total_rate that was already calculated in the optimize function
        mult_text = Text()
        mult_text.append(f"📎 Applied Multipliers: {', '.join(multipliers['applied'])}\n", style="cyan")
        factor = multipliers.get("total_rate", 0.0)
        mult_text.append(f"Total Factor: ×{factor:.2f}  (={factor*100:.0f}% of SG simple)")
        console.print("\n", mult_text)


def _print_calculation_result(result: dict, mult_cfg=None):
    """Print a comprehensive, user-friendly tax calculation result."""
    console, Panel, Text, Table = _create_console_with_imports()
    
    # Extract key information
    income_sg = result.get('income_sg', 0)
    income_fed = result.get('income_fed', 0) 
    income = result.get('income', 0)
    federal_tax = result.get('federal', 0)
    sg_simple = result.get('sg_simple', 0)
    sg_after_mult = result.get('sg_after_mult', 0)
    total_tax = result.get('total', 0)
    avg_rate = result.get('avg_rate', 0) * 100  # Convert to percentage
    marginal_total = result.get('marginal_total', 0) * 100  # Convert to percentage
    filing_status = result.get('filing_status', 'single')
    picks = result.get('picks', [])
    feuer_warning = result.get('feuer_warning')
    
    # Main tax calculation panel
    calc_text = Text()
    calc_text.append("💰 TAX CALCULATION RESULTS\n\n", style="bold green")
    
    # Show income information
    if income and income_sg == income_fed:
        calc_text.append(f"Taxable Income: {income:,} CHF\n", style="bold cyan")
    else:
        calc_text.append(f"SG Income: {income_sg:,} CHF\n", style="cyan")
        calc_text.append(f"Federal Income: {income_fed:,} CHF\n", style="cyan")
    
    calc_text.append(f"Total Tax: {total_tax:,.2f} CHF\n", style="bold red")
    calc_text.append(f"Average Tax Rate: {avg_rate:.2f}%\n", style="bold yellow")
    calc_text.append(f"Marginal Tax Rate: {marginal_total:.2f}%", style="bold magenta")
    
    # Add FEUER warning if present
    _print_feuer_warning_if_present(calc_text, feuer_warning)
    
    console.print(Panel(calc_text, title="TaxGlide Calculation", border_style="green"))
    
    # Detailed tax breakdown table
    tax_table = Table(title="📊 Tax Component Breakdown", show_header=True, header_style="bold blue")
    tax_table.add_column("Tax Component", style="cyan")
    tax_table.add_column("Amount (CHF)", justify="right", style="green")
    tax_table.add_column("Effective Rate", justify="right", style="yellow")
    
    # Calculate effective rates
    base_income = max(income_sg, income_fed) if income_sg != income_fed else income
    fed_rate = (federal_tax / base_income * 100) if base_income > 0 else 0
    sg_simple_rate = (sg_simple / base_income * 100) if base_income > 0 else 0
    sg_after_rate = (sg_after_mult / base_income * 100) if base_income > 0 else 0
    
    tax_table.add_row("Federal Tax", f"{federal_tax:,.2f}", f"{fed_rate:.2f}%")
    tax_table.add_row("SG Simple Tax", f"{sg_simple:,.2f}", f"{sg_simple_rate:.2f}%")
    tax_table.add_row("SG After Multipliers", f"{sg_after_mult:,.2f}", f"{sg_after_rate:.2f}%")
    tax_table.add_row("[bold]Total Tax", f"[bold]{total_tax:,.2f}", f"[bold]{avg_rate:.2f}%")
    
    console.print("\n", tax_table)
    
    # Technical details panel
    details_text = Text()
    details_text.append("🎯 CALCULATION DETAILS\n\n", style="bold blue")
    details_text.append(f"Filing Status: {filing_status.replace('_', ' ').title()}\n")
    details_text.append(f"Marginal Rate (next CHF): {marginal_total:.2f}%\n")
    
    # Show federal marginal info if available
    fed_marginal = result.get('marginal_federal_hundreds', 0) * 100
    if fed_marginal > 0:
        details_text.append(f"Federal Marginal Rate: {fed_marginal:.1f}%\n")
    
    # Calculate multiplier effect
    if sg_simple > 0:
        multiplier_effect = (sg_after_mult / sg_simple) - 1
        details_text.append(f"Multiplier Effect: +{multiplier_effect:.1%} on SG simple tax")
    
    console.print(Panel(details_text, title="Technical Analysis", border_style="blue"))
    
    # Applied multipliers - use shared function to fix the bug!
    if picks and mult_cfg:
        _print_multiplier_info(console, Text, picks, mult_cfg, sg_simple)


def _resolve_incomes(
    income: Optional[int] = None,
    income_sg: Optional[int] = None, 
    income_fed: Optional[int] = None
) -> tuple[int, int]:
    """Resolve income parameters to (sg_income, fed_income) tuple.
    
    Args:
        income: Single income for both SG and Federal (backward compatibility)
        income_sg: Specific SG taxable income
        income_fed: Specific Federal taxable income
        
    Returns:
        (sg_income, fed_income) tuple
        
    Raises:
        ValueError: If invalid combination of parameters provided
    """
    # Scenario 1: Traditional single income (backward compatible)
    if income is not None and income_sg is None and income_fed is None:
        return (income, income)
    
    # Scenario 2: Separate SG and Federal incomes
    if income is None and income_sg is not None and income_fed is not None:
        return (income_sg, income_fed)
    
    # Invalid scenarios
    if income is not None and (income_sg is not None or income_fed is not None):
        raise ValueError(
            "Cannot specify both --income and --income-sg/--income-fed. "
            "Use either --income alone, or both --income-sg and --income-fed together."
        )
    
    if (income_sg is None) != (income_fed is None):  # XOR - only one is provided
        raise ValueError(
            "When using separate incomes, both --income-sg and --income-fed must be provided."
        )
    
    raise ValueError(
        "Must provide either --income, or both --income-sg and --income-fed."
    )


def _calc_with_new_configs(
    sg_cfg, fed_cfg, mult_cfg, 
    sg_income: int, 
    fed_income: int, 
    picks: List[str], 
    filing_status: FilingStatus = "single"
):
    """Calculate taxes with separate cantonal and Federal taxable incomes using new multi-canton configs.
    
    Args:
        sg_cfg: Canton configuration (StGallenConfig format)
        fed_cfg: Federal configuration
        mult_cfg: Multipliers configuration
        sg_income: Canton taxable income
        fed_income: Federal taxable income  
        picks: Multiplier codes to apply
        filing_status: Filing status ("single" or "married_joint")
        
    Returns:
        Dict with tax calculation results
    """
    sg_income_d = chf(sg_income)
    fed_income_d = chf(fed_income)

    sg_simple = simple_tax_sg_with_filing_status(sg_income_d, sg_cfg, filing_status)
    sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks))
    fed = tax_federal_with_filing_status(fed_income_d, fed_cfg, filing_status)

    total = sg_after + fed
    
    # For average rate calculation, use the higher income as base (more conservative)
    base_income = max(sg_income_d, fed_income_d)
    avg_rate = float(total / base_income) if base_income > 0 else 0.0

    # Combined marginal via 1 CHF diff (finite difference) - check both incomes
    eps = Decimal(1)
    sg_marginal = apply_multipliers(
        simple_tax_sg_with_filing_status(sg_income_d + eps, sg_cfg, filing_status), 
        mult_cfg, 
        MultPick(picks)
    ) - sg_after
    fed_marginal = tax_federal_with_filing_status(fed_income_d + eps, fed_cfg, filing_status) - fed
    marginal_total = float(sg_marginal + fed_marginal) / 1.0

    m_fed_h = federal_marginal_hundreds(fed_income_d, fed_cfg)

    return {
        "income_sg": sg_income,
        "income_fed": fed_income,
        "income": sg_income if sg_income == fed_income else None,  # For backward compatibility
        "federal": float(fed),
        "sg_simple": float(sg_simple),
        "sg_after_mult": float(sg_after),
        "total": float(total),
        "avg_rate": avg_rate,
        "marginal_total": marginal_total,
        "marginal_federal_hundreds": m_fed_h,
        "picks": picks,
        "filing_status": filing_status,
    }


@app.command()
def version(
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
    schema_version: bool = typer.Option(False, "--schema-version", help="Include schema version information"),
):
    """Show version information.
    
    Use --json for machine-readable output.
    Use --schema-version to include schema compatibility information.
    """
    try:
        version_data = {
            "version": TAXGLIDE_VERSION,
            "platform": platform.system().lower()
        }
        
        if schema_version:
            version_data["schema_version"] = SCHEMA_VERSION
            version_data["build_date"] = datetime.now(timezone.utc).isoformat()
            
        if json_out:
            response = _create_json_response(version_data)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            version_text = Text()
            version_text.append(f"TaxGlide version {TAXGLIDE_VERSION}\n", style="bold green")
            version_text.append(f"Platform: {platform.system()}\n")
            
            if schema_version:
                version_text.append(f"Schema version: {SCHEMA_VERSION}\n", style="cyan")
                version_text.append(f"Build date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", style="dim")
            
            console.print(Panel(version_text, title="Version Information", border_style="blue"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def calc(
    year: int = typer.Option(..., min=1900, help="Tax year, e.g., 2025"),
    income: Optional[int] = typer.Option(None, min=0, help="Taxable income for both SG and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, min=0, help="St. Gallen taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, min=0, help="Federal taxable income (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip (overrides defaults)"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON"),
    filing_status: str = typer.Option("single", callback=lambda ctx, param, value: _validate_filing_status(value) if value else "single", help="Filing status: single or married_joint"),
    canton: Optional[str] = typer.Option(None, help="Canton to use for calculation (e.g., 'st_gallen')"),
    municipality: Optional[str] = typer.Option(None, help="Municipality to use for calculation (e.g., 'st_gallen_city')"),
):
    """Compute federal + cantonal taxes and show breakdown.
    
    Use either:
      --income 80000                           (same income for both cantonal and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    
    Filing status:
      --filing-status single                   (default - individual filing)
      --filing-status married_joint            (married filing jointly - uses income splitting)
      
    Location:
      --canton st_gallen                       (specify canton, defaults to st_gallen)
      --municipality st_gallen_city            (specify municipality, defaults to st_gallen_city)
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        _handle_json_error(e, json_out)
        return
    
    # Load configuration using new multi-canton approach
    try:
        config, canton_cfg, municipality_cfg, fed_config = _load_configs_new_style(year, canton, municipality, filing_status)
        # Store the actual keys that were resolved
        canton_key = canton if canton else config.defaults["canton"]
        municipality_key = municipality if municipality else config.defaults["municipality"]
    except Exception as e:
        _handle_json_error(e, json_out)
        return
    
    # Convert municipality multipliers to legacy format for compatibility
    from .io.loader import create_legacy_multipliers_config
    mult_cfg = create_legacy_multipliers_config(municipality_cfg)
        
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    # Convert canton config to legacy StGallenConfig for compatibility
    from .engine.models import StGallenConfig
    sg_config = StGallenConfig(
        currency=config.currency,
        model=canton_cfg.model,
        rounding=canton_cfg.rounding,
        brackets=canton_cfg.brackets,
        override=canton_cfg.override
    )

    try:
        res = _calc_with_new_configs(sg_config, fed_config, mult_cfg, sg_income, fed_income, sorted(codes), filing_status)
    except Exception as e:
        _handle_json_error(e, json_out)
        return
    
    # Add FEUER warning if not selected (simplified)
    feuer_item = next((item for item in mult_cfg.items if item.code == 'FEUER'), None)
    if feuer_item and 'FEUER' not in codes:
        # Note: FEUER is typically calculated on the simple tax, which already includes filing status
        sg_simple_base = Decimal(str(res["sg_simple"]))  # already computed with filing status
        potential_feuer_tax = sg_simple_base * Decimal(str(feuer_item.rate))
        res["feuer_warning"] = f"⚠️ Missing FEUER tax: +{potential_feuer_tax:.0f} CHF (add --pick FEUER)"
    
    # Add location information to response
    res["canton_name"] = canton_cfg.name
    res["canton_key"] = canton_key
    res["municipality_name"] = municipality_cfg.name  
    res["municipality_key"] = municipality_key
    
    if json_out:
        response = _create_json_response(res)
        print(json.dumps(response, indent=2))
    else:
        # Clean, user-friendly output for terminal use - pass mult_cfg to fix multiplier display bug
        _print_calculation_result(res, mult_cfg)


@app.command()
def optimize(
    year: int = typer.Option(..., min=1900),
    income: Optional[int] = typer.Option(None, min=0, help="Taxable income for both cantonal and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, min=0, help="Cantonal taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, min=0, help="Federal taxable income (CHF)"),
    max_deduction: int = typer.Option(..., min=0),
    step: int = typer.Option(100, min=1, help="Deduction step (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip"),
    json_out: bool = typer.Option(False, "--json"),
    tolerance_bp: Optional[float] = typer.Option(None, help="Near-max ROI tolerance in basis points (auto-selected by income if not specified)"),
    filing_status: str = typer.Option("single", callback=lambda ctx, param, value: _validate_filing_status(value) if value else "single", help="Filing status: single or married_joint"),
    disable_adaptive: bool = typer.Option(False, "--disable-adaptive", help="Disable adaptive multi-tolerance retry for low utilization"),
    canton: Optional[str] = typer.Option(None, help="Canton to use for calculation (e.g., 'st_gallen')"),
    municipality: Optional[str] = typer.Option(None, help="Municipality to use for calculation (e.g., 'st_gallen_city')"),
):
    """Find optimal deduction amounts with adaptive multi-tolerance optimization.
    
    Use either:
      --income 80000                           (same income for both cantonal and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
    
    Location:
      --canton st_gallen                       (specify canton, defaults to st_gallen)
      --municipality st_gallen_city            (specify municipality, defaults to st_gallen_city)
    
    The optimizer automatically retries with different tolerance settings if low deduction
    utilization is detected (< 30% for incomes > 50K CHF), choosing the best ROI result.
    Use --disable-adaptive to use only the initial tolerance setting.
    
    Note: Optimization assumes the deduction applies equally to both cantonal and Federal incomes.
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        _handle_json_error(e, json_out)
        return
    
    # Load configuration using new multi-canton approach
    try:
        config, canton_cfg, municipality_cfg, fed_cfg = _load_configs_new_style(year, canton, municipality, filing_status)
    except Exception as e:
        _handle_json_error(e, json_out)
        return
    
    # Convert municipality multipliers to legacy format for compatibility
    from .io.loader import create_legacy_multipliers_config
    mult_cfg = create_legacy_multipliers_config(municipality_cfg)
    
    # Convert canton config to legacy StGallenConfig for compatibility
    from .engine.models import StGallenConfig
    sg_cfg = StGallenConfig(
        currency=config.currency,
        model=canton_cfg.model,
        rounding=canton_cfg.rounding,
        brackets=canton_cfg.brackets,
        override=canton_cfg.override
    )
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)

    # Early validation for clearer CLI errors - use the higher income for validation
    base_income = max(sg_income, fed_income)
    try:
        validate_optimization_inputs(Decimal(base_income), max_deduction, 100, step)
    except ValueError as e:
        _handle_json_error(e, json_out)
        return
    
    # Determine tolerance: user-provided or income-adaptive
    if tolerance_bp is None:
        tolerance_bp = _get_adaptive_tolerance_bp(base_income)
        tolerance_source = "auto-selected"
    else:
        tolerance_source = "user-specified"

    # Store original incomes for reference
    sg_income_decimal = Decimal(sg_income)
    fed_income_decimal = Decimal(fed_income)
    
    def calc_fn(current_income: Decimal):
        # Calculate how much was deducted from the base income
        deduction_amount = Decimal(base_income) - current_income
        
        # Apply same deduction to both SG and Federal incomes
        current_sg = sg_income_decimal - deduction_amount
        current_fed = fed_income_decimal - deduction_amount
        
        # Ensure incomes don't go negative
        current_sg = max(current_sg, Decimal(0))
        current_fed = max(current_fed, Decimal(0))
        
        sg_simple = simple_tax_sg_with_filing_status(current_sg, sg_cfg, filing_status)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(codes))
        fed = tax_federal_with_filing_status(current_fed, fed_cfg, filing_status)
        total = sg_after + fed
        return {"total": total, "federal": fed}

    # Provide a context function so optimizer can narrate federal bracket before/after
    def context_fn(current_income: Decimal):
        deduction_amount = Decimal(base_income) - current_income
        current_sg = max(sg_income_decimal - deduction_amount, Decimal(0))
        current_fed = max(fed_income_decimal - deduction_amount, Decimal(0))
        return {
            "federal_segment": federal_segment_info(current_fed, fed_cfg),
            "sg_bracket": sg_bracket_info(current_sg, sg_cfg),
        }

    # Cache calc_fn for performance - optimizer may call identical incomes multiple times
    from functools import lru_cache
    
    @lru_cache(maxsize=None)
    def _calc_cached(y: Decimal):
        return calc_fn(y)
    
    # Use adaptive optimization by default, unless disabled
    if disable_adaptive:
        out = optimize_deduction(
            Decimal(base_income),  # Use higher income as baseline for optimization
            max_deduction,
            step,
            _calc_cached,
            context_fn=context_fn,
            roi_tolerance_bp=tolerance_bp,
        )
    else:
        out = optimize_deduction_adaptive(
            Decimal(base_income),  # Use higher income as baseline for optimization
            max_deduction,
            step,
            _calc_cached,
            context_fn=context_fn,
            initial_roi_tolerance_bp=tolerance_bp,
            enable_adaptive_retry=True,
        )

    # Enhance output with separate income information if applicable
    if out.get("sweet_spot") is not None:
        sweet_spot = out["sweet_spot"]
        deduction = sweet_spot["deduction"]
        
        # Calculate separate new incomes after deduction
        new_sg_income = sg_income - deduction
        new_fed_income = fed_income - deduction
        
        # Add income information (simplified)
        if sg_income != fed_income:
            sweet_spot["income_details"] = {
                "original_sg": sg_income,
                "original_fed": fed_income,
                "after_deduction_sg": float(new_sg_income),
                "after_deduction_fed": float(new_fed_income)
            }
        
        # Add concise multiplier info with FEUER warning if needed
        sweet_spot["multipliers"] = {
            "applied": sorted(codes),
            "total_rate": float(sum(Decimal(str(item.rate)) for item in mult_cfg.items if item.code in codes))
        }
        
        # Add FEUER warning if not selected (consolidated)
        feuer_item = next((item for item in mult_cfg.items if item.code == 'FEUER'), None)
        if feuer_item and 'FEUER' not in codes:
            current_sg = max(sg_income_decimal - Decimal(deduction), Decimal(0))
            sg_simple_at_spot = simple_tax_sg_with_filing_status(current_sg, sg_cfg, filing_status)
            potential_feuer_tax = float(sg_simple_at_spot * Decimal(str(feuer_item.rate)))
            sweet_spot["multipliers"]["feuer_warning"] = f"⚠️ Missing FEUER tax: +{potential_feuer_tax:.0f} CHF (add --pick FEUER)"
        
        # Add utilization warnings based on technical ROI plateau vs deduction space analysis
        utilization_ratio = deduction / max_deduction
        roi = (sweet_spot["tax_saved_absolute"] / deduction * 100) if deduction > 0 else 0
        
        if utilization_ratio > 0.70:  # High utilization (>70%)
            sweet_spot["utilization_warning"] = {
                "type": "high_utilization",
                "utilization_percent": utilization_ratio * 100,
                "message": f"⚠️ High utilization ({utilization_ratio:.1%}): The ROI plateau from tax bracket transitions "
                          f"spans most of your {max_deduction:,} CHF deduction space. This happens when the natural "
                          f"width of tax optimization opportunities matches your available deduction limit. "
                          f"Try '--tolerance-bp {tolerance_bp * 0.5:.0f}' to find a smaller deduction within the plateau.",
                "technical_note": "Tax bracket ROI plateaus have natural widths (~5-8K CHF) independent of your deduction limit."
            }
        elif utilization_ratio < 0.10:  # Very low utilization (<10%)
            sweet_spot["utilization_warning"] = {
                "type": "low_utilization",
                "utilization_percent": utilization_ratio * 100,
                "roi_percent": roi,
                "message": f"⚠️ Low utilization ({utilization_ratio:.1%}): The algorithm found a narrow ROI peak at "
                          f"{deduction:,} CHF, but you have {max_deduction:,} CHF available. This happens when tax bracket "
                          f"transitions create sharp optimization points that are much smaller than your deduction space. "
                          f"Try '--tolerance-bp {tolerance_bp * 2:.0f}' to explore larger deductions with potentially better absolute savings.",
                "technical_note": "Small ROI peaks often indicate bracket boundary effects - larger deductions may provide more total savings."
            }
        
        if sg_income == fed_income:
            # Legacy single income case - keep simple output
            sweet_spot["new_income"] = float(new_sg_income)  # Same for both
        else:
            # Separate income case - new_income for compatibility, details in income_details
            sweet_spot["new_income"] = float(max(new_sg_income, new_fed_income))

    # prettify Decimals for JSON friendliness
    def coerce(d):
        from decimal import Decimal
        if isinstance(d, Decimal):
            return float(d)
        elif isinstance(d, dict):
            return {k: coerce(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [coerce(x) for x in d]
        return d

    # Add basic multiplier info at top level
    out["multipliers_applied"] = sorted(codes)
    
    # Simplify output by hiding overly verbose sections
    if out.get("sweet_spot") and "why" in out["sweet_spot"]:
        why = out["sweet_spot"]["why"]
        # Keep only essential info
        simplified_why = {
            "roi_percent": why.get("roi_at_spot_percent"),
            "plateau_width_chf": why.get("plateau_width_chf"),
            "federal_bracket_changed": why.get("federal_bracket_changed"),
            "marginal_rate_percent": why.get("local_marginal_percent_at_spot")
        }
        # Add notes if they exist
        if why.get("notes"):
            simplified_why["notes"] = why["notes"]
            
        out["sweet_spot"]["optimization_summary"] = simplified_why
        # Remove verbose why section
        del out["sweet_spot"]["why"]
        
    # Remove redundant marginal info at top level (it's in optimization_summary now)
    out.pop("local_marginal_percent_at_best", None)
    out.pop("local_marginal_percent_at_spot", None)
    
    out = {k: coerce(v) for k, v in out.items()}
    
    # Add location information to response
    out["canton_name"] = canton_cfg.name
    out["canton_key"] = canton if canton else config.defaults["canton"]
    out["municipality_name"] = municipality_cfg.name  
    out["municipality_key"] = municipality if municipality else config.defaults["municipality"]
    
    if json_out:
        # Full detailed JSON output for programmatic use
        tolerance_explanation = {
            "tolerance_used_bp": tolerance_bp,
            "tolerance_percent": tolerance_bp / 100.0,
            "tolerance_source": tolerance_source,
            "explanation": f"Tolerance {tolerance_bp:.1f} basis points ({tolerance_bp/100:.2f}%) {tolerance_source} based on income {base_income:,} CHF. "
                          f"This sets how close to the maximum ROI a deduction must be to be considered 'near-optimal'. "
                          f"Higher incomes use wider tolerances because ROI curves are flatter at higher tax brackets."
        }
        out["tolerance_info"] = tolerance_explanation
        response = _create_json_response(out)
        print(json.dumps(response, indent=2))
    else:
        # Clean, user-friendly output for terminal use
        _print_optimization_result(out, tolerance_bp, tolerance_source, base_income, max_deduction)


@app.command()
def plot(
    year: int = typer.Option(...),
    min: int = typer.Option(..., help="Min income"),
    max: int = typer.Option(..., help="Max income"),
    step: int = typer.Option(100),
    pick: List[str] = typer.Option([], help="Codes to pick"),
    skip: List[str] = typer.Option([], help="Codes to skip"),
    out: str = typer.Option("curve.png"),
    # New: optionally annotate with a sweet spot for a given optimization case
    annotate_sweet_spot: bool = typer.Option(False, help="Annotate the plot with a sweet spot/plateau"),
    opt_income: Optional[int] = typer.Option(None, help="Income used for sweet-spot optimization"),
    opt_max_deduction: Optional[int] = typer.Option(None, help="Max deduction for optimization"),
    opt_step: int = typer.Option(100, help="Deduction step for optimization"),
    opt_tolerance_bp: float = typer.Option(10.0, help="Tolerance (bp) used for plateau and sweet spot"),
    filing_status: str = typer.Option("single", callback=lambda ctx, param, value: _validate_filing_status(value) if value else "single", help="Filing status: single or married_joint"),
    canton: Optional[str] = typer.Option(None, help="Canton to use for calculation (e.g., 'st_gallen')"),
    municipality: Optional[str] = typer.Option(None, help="Municipality to use for calculation (e.g., 'st_gallen_city')"),
):
    """
    Plot the tax curve. If --annotate-sweet-spot is set (and opt_* provided),
    the figure will show a shaded plateau and a vertical line at the sweet spot.
    """
    # Load configuration using new multi-canton approach
    config, canton_cfg, municipality_cfg, fed_cfg = _load_configs_new_style(year, canton, municipality, filing_status)
    
    # Convert municipality multipliers to legacy format for compatibility
    from .io.loader import create_legacy_multipliers_config
    mult_cfg = create_legacy_multipliers_config(municipality_cfg)
    
    # Convert canton config to legacy StGallenConfig for compatibility
    from .engine.models import StGallenConfig
    sg_cfg = StGallenConfig(
        currency=config.currency,
        model=canton_cfg.model,
        rounding=canton_cfg.rounding,
        brackets=canton_cfg.brackets,
        override=canton_cfg.override
    )
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)
    picks_sorted = sorted(codes)

    # Build curve
    pts = []
    for x in range(min, max + 1, step):
        # small inline compute (no optimizer), same logic as _calc_once
        inc_d = chf(x)
        sg_simple = simple_tax_sg_with_filing_status(inc_d, sg_cfg, filing_status)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
        fed = tax_federal_with_filing_status(inc_d, fed_cfg, filing_status)
        total = sg_after + fed
        pts.append((x, total))

    annotations: Optional[Dict[str, Any]] = None

    if annotate_sweet_spot and (opt_income is not None) and (opt_max_deduction is not None):
        # Optimizer setup mirrors the optimize command
        def calc_fn(inc: Decimal):
            sg_simple = simple_tax_sg_with_filing_status(inc, sg_cfg, filing_status)
            sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
            fed = tax_federal_with_filing_status(inc, fed_cfg, filing_status)
            total = sg_after + fed
            return {"total": total, "federal": fed}

        # safety: reuse validate
        try:
            validate_optimization_inputs(Decimal(opt_income), int(opt_max_deduction), 100, opt_step)
        except ValueError as e:
            rprint({"warning": f"Cannot annotate sweet spot: {e}"})
            annotations = None
        else:
            res = optimize_deduction(
                Decimal(opt_income),
                int(opt_max_deduction),
                opt_step,
                calc_fn,
                roi_tolerance_bp=opt_tolerance_bp,
            )
            sweet = res.get("sweet_spot")
            plateau = res.get("plateau_near_max_roi")

            if sweet and plateau:
                d_spot = int(sweet["deduction"])
                sweet_income = float(opt_income - d_spot)

                # compute total at sweet spot income to place the marker nicely
                t_inc_d = chf(sweet_income)
                sg_simple = simple_tax_sg_with_filing_status(t_inc_d, sg_cfg, filing_status)
                sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
                fed = tax_federal_with_filing_status(t_inc_d, fed_cfg, filing_status)
                sweet_total = float(sg_after + fed)

                # plateau band in income space
                d_min = int(plateau["min_d"])
                d_max = int(plateau["max_d"])
                annotations = {
                    "sweet_spot_income": sweet_income,
                    "sweet_spot_total": sweet_total,
                    "plateau_income_min": float(opt_income - d_max),
                    "plateau_income_max": float(opt_income - d_min),
                    "label": f"Sweet spot (deduct {d_spot} CHF)",
                }
            else:
                rprint({"info": "No sweet spot/plateau found to annotate."})

    plot_curve(pts, out, annotations=annotations)
    rprint({"saved": out, "annotated": bool(annotations)})


@app.command()
def scan(
    year: int = typer.Option(..., min=1900, help="Tax year (e.g., 2025)"),
    income: Optional[int] = typer.Option(None, min=0, help="Original taxable income for both cantonal and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, min=0, help="Cantonal taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, min=0, help="Federal taxable income (CHF)"),
    max_deduction: int = typer.Option(..., min=0, help="Max deduction to explore (CHF)"),
    d_step: int = typer.Option(100, min=1, help="Deduction increment (CHF)"),
    pick: List[str] = typer.Option([], help="Codes to pick (multipliers)"),
    skip: List[str] = typer.Option([], help="Codes to skip (multipliers)"),
    out: str = typer.Option("scan.csv", help="Output CSV path"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON instead of writing CSV"),
    include_local_marginal: bool = typer.Option(True, help="Compute local marginal % using Δ100"),
    filing_status: str = typer.Option("single", callback=lambda ctx, param, value: _validate_filing_status(value) if value else "single", help="Filing status: single or married_joint"),
    canton: Optional[str] = typer.Option(None, help="Canton to use for calculation (e.g., 'st_gallen')"),
    municipality: Optional[str] = typer.Option(None, help="Municipality to use for calculation (e.g., 'st_gallen_city')"),
):
    """
    Produce a dense table of values for deductions d = 0..max_deduction (step=d_step):
      - d, new_income
      - total tax, saved, ROI (%)
      - Cantonal simple, cantonal after multipliers, Federal
      - federal segment (from/to/per100) for each new_income
      - local marginal percent (Δ100) around each new_income (optional)
    
    Use either:
      --income 80000                           (same income for both cantonal and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
      
    Location:
      --canton st_gallen                       (specify canton, defaults to st_gallen)
      --municipality st_gallen_city            (specify municipality, defaults to st_gallen_city)
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        _handle_json_error(e, json_out)
        return
        
    # Load configuration using new multi-canton approach
    try:
        config, canton_cfg, municipality_cfg, fed_cfg = _load_configs_new_style(year, canton, municipality, filing_status)
    except Exception as e:
        _handle_json_error(e, json_out)
        return
    
    # Convert municipality multipliers to legacy format for compatibility
    from .io.loader import create_legacy_multipliers_config
    mult_cfg = create_legacy_multipliers_config(municipality_cfg)
    
    # Convert canton config to legacy StGallenConfig for compatibility
    from .engine.models import StGallenConfig
    sg_cfg = StGallenConfig(
        currency=config.currency,
        model=canton_cfg.model,
        rounding=canton_cfg.rounding,
        brackets=canton_cfg.brackets,
        override=canton_cfg.override
    )
    default_picks = [i.code for i in mult_cfg.items if i.default_selected]
    codes = set(default_picks) | set(pick)
    codes -= set(skip)
    picks_sorted = sorted(codes)

    # Validate bounds using higher income
    base_income = max(sg_income, fed_income)
    try:
        validate_optimization_inputs(Decimal(base_income), max_deduction, 0, max(1, d_step))
    except ValueError as e:
        _handle_json_error(e, json_out)
        return

    # Helper to compute totals with separate SG and Federal incomes
    def calc_all(sg_inc: Decimal, fed_inc: Decimal):
        sg_simple = simple_tax_sg_with_filing_status(sg_inc, sg_cfg, filing_status)
        sg_after = apply_multipliers(sg_simple, mult_cfg, MultPick(picks_sorted))
        fed = tax_federal_with_filing_status(fed_inc, fed_cfg, filing_status)
        total = sg_after + fed
        return sg_simple, sg_after, fed, total

    SG0 = Decimal(sg_income)
    FED0 = Decimal(fed_income)
    _, _, _, T0 = calc_all(SG0, FED0)

    rows: List[Dict[str, Any]] = []
    eps = Decimal(100)

    for d in range(0, max_deduction + 1, max(1, d_step)):
        sg_y = SG0 - Decimal(d)
        fed_y = FED0 - Decimal(d)
        
        # Ensure incomes don't go negative
        sg_y = max(sg_y, Decimal(0))
        fed_y = max(fed_y, Decimal(0))

        sg_simple, sg_after, fed, total = calc_all(sg_y, fed_y)
        saved = T0 - total
        roi = (saved / Decimal(d)) if d > 0 else Decimal(0)
        roi_pct = float(roi * 100) if d > 0 else 0.0

        # federal segment info at current federal income
        fseg = federal_segment_info(fed_y, fed_cfg)

        # local marginal around current incomes (Δ100) if requested and feasible
        local_marginal_pct = None
        if include_local_marginal:
            if sg_y >= eps and fed_y >= eps:
                _, _, _, t_hi = calc_all(sg_y, fed_y)
                _, _, _, t_lo = calc_all(sg_y - eps, fed_y - eps)
                local_marginal_pct = float((t_hi - t_lo) / eps * 100)
            else:
                local_marginal_pct = float(0.0)

        row_data = {
            "deduction": d,
            "new_income": float(max(sg_y, fed_y)),  # Keep for backward compatibility
            "total_tax": float(total),
            "saved": float(saved),
            "roi_percent": roi_pct,
            "sg_simple": float(sg_simple),
            "sg_after_multipliers": float(sg_after),
            "federal": float(fed),
            "federal_from": fseg["from"],
            "federal_to": fseg["to"] if fseg["to"] is not None else None,
            "federal_per100": fseg["per100"],
            "local_marginal_percent": local_marginal_pct,
        }
        
        # Add separate income details if different incomes were used
        if sg_income != fed_income:
            row_data["new_income_sg"] = float(sg_y)
            row_data["new_income_fed"] = float(fed_y)
            
        rows.append(row_data)

    if json_out:
        response = _create_json_response(rows)
        print(json.dumps(response, indent=2))
        return

    # write CSV
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build fieldnames dynamically to include separate income fields when applicable
    if rows:
        fieldnames = list(rows[0].keys())
    else:
        fieldnames = [
            "deduction","new_income","total_tax","saved","roi_percent",
            "sg_simple","sg_after_multipliers","federal",
            "federal_from","federal_to","federal_per100","local_marginal_percent"
        ]
        # Add separate income fields if different incomes were used
        if sg_income != fed_income:
            fieldnames.insert(2, "new_income_sg")  # Insert after new_income
            fieldnames.insert(3, "new_income_fed")
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    rprint({"saved": str(out_path), "rows": len(rows)})

@app.command()
def validate(
    year: int = typer.Option(..., help="Tax year to validate"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Validate configuration files for given year."""
    try:
        config = load_switzerland_config(CONFIG_ROOT, year)
        result_data = {"status": "valid", "year": year, "message": "All configurations valid"}
        
        if json_out:
            response = _create_json_response(result_data)
            print(json.dumps(response, indent=2))
        else:
            rprint(result_data)
    except Exception as e:
        if json_out:
            error_response = _create_json_error("VALIDATION_ERROR", str(e), {"year": year})
            print(json.dumps(error_response, indent=2))
        else:
            rprint({"status": "invalid", "year": year, "error": str(e)})
        raise typer.Exit(code=ERROR_CODES["VALIDATION_ERROR"])

@app.command() 
def compare_brackets(
    year: int = typer.Option(..., min=1900),
    income: Optional[int] = typer.Option(None, min=0, help="Taxable income for both cantonal and Federal (CHF)"),
    income_sg: Optional[int] = typer.Option(None, min=0, help="Cantonal taxable income (CHF)"),
    income_fed: Optional[int] = typer.Option(None, min=0, help="Federal taxable income (CHF)"),
    deduction: int = typer.Option(0, "--deduction", min=0, help="Amount to deduct"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
    filing_status: str = typer.Option("single", callback=lambda ctx, param, value: _validate_filing_status(value) if value else "single", help="Filing status: single or married_joint"),
    canton: Optional[str] = typer.Option(None, help="Canton to use for calculation (e.g., 'st_gallen')"),
    municipality: Optional[str] = typer.Option(None, help="Municipality to use for calculation (e.g., 'st_gallen_city')"),
):
    """Show which tax brackets apply before/after deduction.
    
    Use either:
      --income 80000                           (same income for both cantonal and Federal)
      --income-sg 78000 --income-fed 80000     (different incomes due to different deductions)
      
    Location:
      --canton st_gallen                       (specify canton, defaults to st_gallen)
      --municipality st_gallen_city            (specify municipality, defaults to st_gallen_city)
    """
    try:
        sg_income, fed_income = _resolve_incomes(income, income_sg, income_fed)
    except ValueError as e:
        _handle_json_error(e, json_out)
        return
        
    # Load configuration using new multi-canton approach
    try:
        config, canton_cfg, municipality_cfg, fed_cfg = _load_configs_new_style(year, canton, municipality, filing_status)
    except Exception as e:
        _handle_json_error(e, json_out)
        return
    
    # Convert canton config to legacy StGallenConfig for compatibility
    from .engine.models import StGallenConfig
    sg_cfg = StGallenConfig(
        currency=config.currency,
        model=canton_cfg.model,
        rounding=canton_cfg.rounding,
        brackets=canton_cfg.brackets,
        override=canton_cfg.override
    )
    
    # Original incomes
    original_sg_income = chf(sg_income)
    original_fed_income = chf(fed_income)
    
    # Adjusted incomes (after deduction)
    adjusted_sg_income = chf(max(0, sg_income - deduction))
    adjusted_fed_income = chf(max(0, fed_income - deduction))

    
    # Federal bracket info
    fed_before = federal_segment_info(original_fed_income, fed_cfg)
    fed_after = federal_segment_info(adjusted_fed_income, fed_cfg)
    # SG bracket info
    sg_before = sg_bracket_info(original_sg_income, sg_cfg)
    sg_after = sg_bracket_info(adjusted_sg_income, sg_cfg)
    
    result_data = {
        "original_sg_income": sg_income,
        "original_fed_income": fed_income,
        "adjusted_sg_income": float(adjusted_sg_income),
        "adjusted_fed_income": float(adjusted_fed_income),
        "deduction_amount": deduction,
        "federal_bracket_before": fed_before,
        "federal_bracket_after": fed_after,
        "federal_bracket_changed": fed_before != fed_after,
        "sg_bracket_before": sg_before,
        "sg_bracket_after": sg_after,
        "sg_bracket_changed": sg_before != sg_after,
    }
    
    if json_out:
        response = _create_json_response(result_data)
        print(json.dumps(response, indent=2))
    else:
        rprint(result_data)


@app.command()
def locations(
    year: int = typer.Option(2025, help="Tax year to load locations for"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Get available cantons and municipalities from configuration.
    
    Returns the list of supported cantons and their municipalities based on 
    the switzerland.yaml configuration file for the specified year.
    """
    try:
        # Load the switzerland configuration
        config = load_switzerland_config(CONFIG_ROOT, year)
        
        # Build cantons list with municipalities
        cantons_data = []
        for canton_key, canton_config in config.cantons.items():
            municipalities_data = []
            
            # Add municipalities for this canton
            if hasattr(canton_config, 'municipalities') and canton_config.municipalities:
                for municipality_key, municipality_config in canton_config.municipalities.items():
                    municipalities_data.append({
                        "name": municipality_config.name,
                        "key": municipality_key
                    })
            
            cantons_data.append({
                "name": canton_config.name,
                "key": canton_key,
                "municipalities": municipalities_data
            })
        
        # Prepare response data
        result_data = {
            "cantons": cantons_data,
            "defaults": {
                "canton": config.defaults["canton"],
                "municipality": config.defaults["municipality"]
            }
        }
        
        if json_out:
            response = _create_json_response(result_data)
            print(json.dumps(response, indent=2))
        else:
            rprint(result_data)
            
    except Exception as e:
        if json_out:
            error_response = _create_json_error("VALIDATION_ERROR", str(e), {"year": year})
            print(json.dumps(error_response, indent=2))
        else:
            rprint({"status": "error", "year": year, "error": str(e)})
        raise typer.Exit(code=ERROR_CODES["VALIDATION_ERROR"])


@app.command()
def get_federal_segments(
    year: int = typer.Option(..., help="Tax year to get federal segments for"),
    filing_status: str = typer.Option("single", callback=lambda ctx, param, value: _validate_filing_status(value) if value else "single", help="Filing status: single or married_joint"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Get federal tax segments for a specific year and filing status.
    
    Returns the detailed federal tax bracket configuration for editing.
    """
    try:
        config_manager = ConfigManager(CONFIG_ROOT)
        
        if not config_manager.year_exists(year):
            raise ValueError(f"Configuration for year {year} does not exist")
        
        config = config_manager.load_config(year)
        
        # Get the federal config for the filing status
        fed_config = getattr(config.federal, filing_status)
        
        # Convert segments to dict format
        segments_data = []
        for segment in fed_config.segments:
            segments_data.append({
                "from": segment.from_,
                "to": segment.to,
                "at_income": segment.at_income,
                "base_tax_at": segment.base_tax_at,
                "per100": segment.per100
            })
        
        result_data = {
            "year": year,
            "filing_status": filing_status,
            "segments": segments_data,
            "segments_count": len(segments_data)
        }
        
        if json_out:
            response = _create_json_response(result_data)
            print(json.dumps(response, indent=2))
        else:
            rprint(result_data)
            
    except Exception as e:
        if json_out:
            error_response = _create_json_error("VALIDATION_ERROR", str(e), {"year": year, "filing_status": filing_status})
            print(json.dumps(error_response, indent=2))
        else:
            rprint({"status": "error", "year": year, "filing_status": filing_status, "error": str(e)})
        raise typer.Exit(code=ERROR_CODES["VALIDATION_ERROR"])


@app.command()
def config_summary(
    year: int = typer.Option(2025, help="Tax year to get configuration summary for"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Get comprehensive summary of tax configuration for a year.
    
    Shows overview of cantons, municipalities, tax brackets, and other
    configuration details for the specified year.
    """
    try:
        config_manager = ConfigManager(CONFIG_ROOT)
        
        if not config_manager.year_exists(year):
            raise ValueError(f"Configuration for year {year} does not exist")
        
        summary = config_manager.get_config_summary(year)
        
        if json_out:
            response = _create_json_response(summary)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, Table = _create_console_with_imports()
            
            # Main summary
            summary_text = Text()
            summary_text.append(f"📋 TAX CONFIGURATION SUMMARY - {year}\n\n", style="bold green")
            summary_text.append(f"Country: {summary['country']}\n", style="cyan")
            summary_text.append(f"Currency: {summary['currency']}\n", style="cyan")
            summary_text.append(f"Schema Version: {summary['schema_version']}\n", style="dim")
            summary_text.append(f"Cantons: {summary['canton_count']}\n", style="yellow")
            summary_text.append(f"Default Canton: {summary['defaults']['canton']} / {summary['defaults']['municipality']}")
            
            console.print(Panel(summary_text, title="Configuration Overview", border_style="green"))
            
            # Cantons table
            cantons_table = Table(title="📍 Available Cantons & Municipalities", show_header=True, header_style="bold blue")
            cantons_table.add_column("Canton", style="cyan")
            cantons_table.add_column("Abbreviation", justify="center")
            cantons_table.add_column("Tax Brackets", justify="right", style="yellow")
            cantons_table.add_column("Municipalities", justify="right", style="green")
            cantons_table.add_column("Municipality Names", style="dim")
            
            for canton in summary['cantons']:
                muni_names = ", ".join([m['name'] for m in canton['municipalities']])
                cantons_table.add_row(
                    canton['name'],
                    canton['abbreviation'],
                    str(canton['bracket_count']),
                    str(canton['municipality_count']),
                    muni_names[:50] + "..." if len(muni_names) > 50 else muni_names
                )
            
            console.print("\n", cantons_table)
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def list_years(
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """List all available tax years.
    
    Shows which tax years have configuration files available.
    """
    try:
        config_manager = ConfigManager(CONFIG_ROOT)
        years = config_manager.get_available_years()
        
        result_data = {
            "available_years": years,
            "count": len(years)
        }
        
        if json_out:
            response = _create_json_response(result_data)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            years_text = Text()
            years_text.append("📅 AVAILABLE TAX YEARS\n\n", style="bold green")
            
            if years:
                years_text.append(f"Found {len(years)} tax year(s):\n", style="cyan")
                for year in years:
                    years_text.append(f"• {year}\n", style="yellow")
            else:
                years_text.append("No tax years found in configuration directory.", style="red")
            
            console.print(Panel(years_text, title="Tax Years", border_style="blue"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def create_year(
    source_year: int = typer.Option(..., help="Year to copy configuration from"),
    target_year: int = typer.Option(..., help="New year to create"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite target year if it exists"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Create new tax year by copying configuration from existing year.
    
    This copies the entire year directory including all configuration files.
    Use --overwrite to replace existing year configurations.
    """
    try:
        config_manager = ConfigManager(CONFIG_ROOT)
        
        result = config_manager.create_year(source_year, target_year, overwrite)
        
        if json_out:
            response = _create_json_response(result)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append("📋 YEAR CREATION SUCCESSFUL\n\n", style="bold green")
            result_text.append(f"Source Year: {result['source_year']}\n", style="cyan")
            result_text.append(f"Target Year: {result['target_year']}\n", style="yellow")
            result_text.append(f"Status: {result['message']}", style="green")
            
            console.print(Panel(result_text, title="Create Year", border_style="green"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def update_federal_brackets(
    year: int = typer.Option(..., help="Tax year to update"),
    filing_status: str = typer.Option(..., help="Filing status: single or married_joint"),
    segments_file: str = typer.Option(..., help="JSON file containing federal tax segments"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Update federal tax brackets from JSON file.
    
    The JSON file should contain an array of segment objects with:
    - from: Lower income threshold
    - to: Upper income threshold (null for last segment)
    - at_income: Income level for base tax calculation
    - base_tax_at: Base tax amount at the income level
    - per100: Tax rate per 100 CHF above base
    
    Example JSON structure:
    [
        {"from": 0, "to": 15200, "at_income": 15200, "base_tax_at": 0.0, "per100": 0.0},
        {"from": 15200, "to": 33200, "at_income": 15200, "base_tax_at": 0.0, "per100": 0.77}
    ]
    """
    try:
        import json as json_mod
        
        # Validate filing status
        filing_status = _validate_filing_status(filing_status)
        
        # Load segments from file
        segments_path = Path(segments_file)
        if not segments_path.exists():
            raise FileNotFoundError(f"Segments file not found: {segments_file}")
        
        with open(segments_path, 'r') as f:
            segments_data = json_mod.load(f)
        
        if not isinstance(segments_data, list):
            raise ValueError("Segments file must contain a JSON array of segment objects")
        
        config_manager = ConfigManager(CONFIG_ROOT)
        result = config_manager.update_federal_brackets(year, filing_status, segments_data)
        
        if json_out:
            response = _create_json_response(result)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append("💰 FEDERAL BRACKETS UPDATED\n\n", style="bold green")
            result_text.append(f"Year: {year}\n", style="cyan")
            result_text.append(f"Filing Status: {filing_status}\n", style="yellow")
            result_text.append(f"Segments Updated: {result['segments_count']}\n", style="green")
            result_text.append(f"Status: {result['message']}", style="green")
            
            if result.get('backup_file'):
                result_text.append(f"\n\nBackup created: {result['backup_file']}", style="dim")
            
            console.print(Panel(result_text, title="Update Federal Brackets", border_style="green"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def create_canton(
    year: int = typer.Option(..., help="Tax year to add canton to"),
    canton_key: str = typer.Option(..., help="Unique key for the canton (e.g., 'zurich')"),
    canton_file: str = typer.Option(..., help="JSON file containing canton configuration"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Create new canton from JSON configuration file.
    
    The JSON file should contain canton configuration with:
    - name: Full canton name
    - abbreviation: Short abbreviation (e.g., 'ZH')
    - brackets: Array of tax brackets with lower, width, rate_percent
    - rounding: Rounding configuration
    - municipalities: Municipality definitions
    
    Example canton structure:
    {
        "name": "Zurich",
        "abbreviation": "ZH",
        "brackets": [
            {"lower": 0, "width": 10000, "rate_percent": 0.0},
            {"lower": 10000, "width": 20000, "rate_percent": 5.0}
        ],
        "rounding": {"taxable_step": 1, "tax_round_to": 0, "scope": "as_official"},
        "municipalities": {...}
    }
    """
    try:
        import json as json_mod
        
        # Load canton data from file
        canton_path = Path(canton_file)
        if not canton_path.exists():
            raise FileNotFoundError(f"Canton file not found: {canton_file}")
        
        with open(canton_path, 'r') as f:
            canton_data = json_mod.load(f)
        
        if not isinstance(canton_data, dict):
            raise ValueError("Canton file must contain a JSON object with canton configuration")
        
        config_manager = ConfigManager(CONFIG_ROOT)
        result = config_manager.create_canton(year, canton_key, canton_data)
        
        if json_out:
            response = _create_json_response(result)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append("🏛️ CANTON CREATED\n\n", style="bold green")
            result_text.append(f"Year: {year}\n", style="cyan")
            result_text.append(f"Canton Key: {result['canton_key']}\n", style="yellow")
            result_text.append(f"Canton Name: {result['canton_name']}\n", style="green")
            result_text.append(f"Status: {result['message']}", style="green")
            
            if result.get('backup_file'):
                result_text.append(f"\n\nBackup created: {result['backup_file']}", style="dim")
            
            console.print(Panel(result_text, title="Create Canton", border_style="green"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def update_canton(
    year: int = typer.Option(..., help="Tax year to update canton in"),
    canton_key: str = typer.Option(..., help="Canton key to update"),
    canton_file: str = typer.Option(..., help="JSON file containing updated canton configuration"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Update existing canton from JSON configuration file.
    
    Updates all canton properties including tax brackets, rounding rules,
    and municipalities. See create_canton for JSON file format.
    """
    try:
        import json as json_mod
        
        # Load canton data from file
        canton_path = Path(canton_file)
        if not canton_path.exists():
            raise FileNotFoundError(f"Canton file not found: {canton_file}")
        
        with open(canton_path, 'r') as f:
            canton_data = json_mod.load(f)
        
        if not isinstance(canton_data, dict):
            raise ValueError("Canton file must contain a JSON object with canton configuration")
        
        config_manager = ConfigManager(CONFIG_ROOT)
        result = config_manager.update_canton(year, canton_key, canton_data)
        
        if json_out:
            response = _create_json_response(result)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append("🏛️ CANTON UPDATED\n\n", style="bold green")
            result_text.append(f"Year: {year}\n", style="cyan")
            result_text.append(f"Canton Key: {result['canton_key']}\n", style="yellow")
            result_text.append(f"Canton Name: {result['canton_name']}\n", style="green")
            result_text.append(f"Status: {result['message']}", style="green")
            
            if result.get('backup_file'):
                result_text.append(f"\n\nBackup created: {result['backup_file']}", style="dim")
            
            console.print(Panel(result_text, title="Update Canton", border_style="green"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def delete_canton(
    year: int = typer.Option(..., help="Tax year to delete canton from"),
    canton_key: str = typer.Option(..., help="Canton key to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm deletion without prompting"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Delete canton from configuration.
    
    This permanently removes the canton and all its municipalities.
    Use --confirm to skip the confirmation prompt.
    """
    try:
        config_manager = ConfigManager(CONFIG_ROOT)
        
        # Load config to get canton name for confirmation
        config = config_manager.load_config(year)
        if canton_key not in config.cantons:
            raise ValueError(f"Canton '{canton_key}' does not exist in year {year}")
        
        canton_name = config.cantons[canton_key].name
        
        # Confirmation prompt (skip in JSON mode or if --confirm used)
        if not json_out and not confirm:
            confirmation = typer.confirm(
                f"Are you sure you want to delete canton '{canton_name}' ({canton_key}) from year {year}? "
                "This will permanently remove the canton and all its municipalities."
            )
            if not confirmation:
                rprint("❌ Deletion cancelled.", style="yellow")
                return
        
        result = config_manager.delete_canton(year, canton_key)
        
        if json_out:
            response = _create_json_response(result)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append("🗑️ CANTON DELETED\n\n", style="bold red")
            result_text.append(f"Year: {year}\n", style="cyan")
            result_text.append(f"Canton Key: {result['canton_key']}\n", style="yellow")
            result_text.append(f"Canton Name: {result['canton_name']}\n", style="red")
            result_text.append(f"Status: {result['message']}", style="green")
            
            if result.get('backup_file'):
                result_text.append(f"\n\nBackup created: {result['backup_file']}", style="dim")
            
            console.print(Panel(result_text, title="Delete Canton", border_style="red"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def get_canton(
    year: int = typer.Option(..., help="Tax year to get canton from"),
    canton_key: str = typer.Option(..., help="Canton key to retrieve"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Get full canton configuration details.
    
    Returns complete canton configuration including tax brackets,
    municipalities, rounding rules, and all other properties.
    """
    try:
        config_manager = ConfigManager(CONFIG_ROOT)
        config = config_manager.load_config(year)
        
        if canton_key not in config.cantons:
            raise ValueError(f"Canton '{canton_key}' does not exist in year {year}")
        
        canton_config = config.cantons[canton_key]
        
        # Build canton data for output
        canton_data = {
            "name": canton_config.name,
            "abbreviation": canton_config.abbreviation,
            "brackets": [{
                "lower": bracket.lower,
                "width": bracket.width,
                "rate_percent": bracket.rate_percent
            } for bracket in canton_config.brackets],
            "rounding": {
                "taxable_step": canton_config.rounding.taxable_step,
                "tax_round_to": canton_config.rounding.tax_round_to,
                "scope": canton_config.rounding.scope
            },
            "municipalities": {}
        }
        
        # Add municipalities if they exist
        if hasattr(canton_config, 'municipalities') and canton_config.municipalities:
            for muni_key, muni_config in canton_config.municipalities.items():
                canton_data["municipalities"][muni_key] = {
                    "name": muni_config.name,
                    "multipliers": {},
                    "multiplier_order": getattr(muni_config, 'multiplier_order', [])
                }
                
                # Add multipliers if they exist
                if hasattr(muni_config, 'multipliers') and muni_config.multipliers:
                    for mult_key, mult_config in muni_config.multipliers.items():
                        canton_data["municipalities"][muni_key]["multipliers"][mult_key] = {
                            "name": mult_config.name,
                            "code": mult_config.code,
                            "kind": getattr(mult_config, 'kind', 'standard'),  # Default to 'standard' if not present
                            "rate": mult_config.rate,
                            "optional": getattr(mult_config, 'optional', None),
                            "default_selected": mult_config.default_selected
                        }
        
        if json_out:
            response = _create_json_response(canton_data)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append(f"🏛️ {canton_data['name']} ({canton_data['abbreviation']})\n\n", style="bold green")
            result_text.append(f"Tax Brackets: {len(canton_data['brackets'])}\n", style="cyan")
            result_text.append(f"Municipalities: {len(canton_data['municipalities'])}\n", style="yellow")
            result_text.append(f"Rounding: Step {canton_data['rounding']['taxable_step']}, "
                             f"Round to {canton_data['rounding']['tax_round_to']}", style="dim")
            
            console.print(Panel(result_text, title=f"Canton Details - {year}", border_style="green"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def create_municipality(
    year: int = typer.Option(..., help="Tax year to add municipality to"),
    canton_key: str = typer.Option(..., help="Canton key to add municipality to"),
    municipality_key: str = typer.Option(..., help="Unique key for the municipality"),
    municipality_file: str = typer.Option(..., help="JSON file containing municipality configuration"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Create new municipality in a canton from JSON configuration file.
    
    The JSON file should contain municipality configuration with:
    - name: Full municipality name
    - multipliers: Tax multiplier definitions
    - multiplier_order: Order of multiplier display
    
    Example municipality structure:
    {
        "name": "Basel",
        "multipliers": {
            "canton": {"name": "Kanton", "code": "KANTON", "rate": 1.0, "default_selected": true},
            "municipal": {"name": "Gemeinde", "code": "GEMEINDE", "rate": 1.2, "default_selected": true}
        },
        "multiplier_order": ["Kanton", "Gemeinde"]
    }
    """
    try:
        import json as json_mod
        
        # Load municipality data from file
        muni_path = Path(municipality_file)
        if not muni_path.exists():
            raise FileNotFoundError(f"Municipality file not found: {municipality_file}")
        
        with open(muni_path, 'r') as f:
            muni_data = json_mod.load(f)
        
        if not isinstance(muni_data, dict):
            raise ValueError("Municipality file must contain a JSON object with municipality configuration")
        
        config_manager = ConfigManager(CONFIG_ROOT)
        result = config_manager.create_municipality(year, canton_key, municipality_key, muni_data)
        
        if json_out:
            response = _create_json_response(result)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append("🏙️ MUNICIPALITY CREATED\n\n", style="bold green")
            result_text.append(f"Year: {year}\n", style="cyan")
            result_text.append(f"Canton: {result['canton_key']}\n", style="yellow")
            result_text.append(f"Municipality Key: {result['municipality_key']}\n", style="yellow")
            result_text.append(f"Municipality Name: {result['municipality_name']}\n", style="green")
            result_text.append(f"Status: {result['message']}", style="green")
            
            if result.get('backup_file'):
                result_text.append(f"\n\nBackup created: {result['backup_file']}", style="dim")
            
            console.print(Panel(result_text, title="Create Municipality", border_style="green"))
            
    except Exception as e:
        _handle_json_error(e, json_out)


@app.command()
def update_municipality(
    year: int = typer.Option(..., help="Tax year to update municipality in"),
    canton_key: str = typer.Option(..., help="Canton key containing the municipality"),
    municipality_key: str = typer.Option(..., help="Municipality key to update"),
    municipality_file: str = typer.Option(..., help="JSON file containing updated municipality configuration"),
    json_out: bool = typer.Option(False, "--json", help="Output JSON format"),
):
    """Update existing municipality from JSON configuration file.
    
    Updates all municipality properties including multipliers.
    See create_municipality for JSON file format.
    """
    try:
        import json as json_mod
        
        # Load municipality data from file
        muni_path = Path(municipality_file)
        if not muni_path.exists():
            raise FileNotFoundError(f"Municipality file not found: {municipality_file}")
        
        with open(muni_path, 'r') as f:
            muni_data = json_mod.load(f)
        
        if not isinstance(muni_data, dict):
            raise ValueError("Municipality file must contain a JSON object with municipality configuration")
        
        config_manager = ConfigManager(CONFIG_ROOT)
        result = config_manager.update_municipality(year, canton_key, municipality_key, muni_data)
        
        if json_out:
            response = _create_json_response(result)
            print(json.dumps(response, indent=2))
        else:
            console, Panel, Text, _ = _create_console_with_imports()
            
            result_text = Text()
            result_text.append("🏙️ MUNICIPALITY UPDATED\n\n", style="bold green")
            result_text.append(f"Year: {year}\n", style="cyan")
            result_text.append(f"Canton: {result['canton_key']}\n", style="yellow")
            result_text.append(f"Municipality Key: {result['municipality_key']}\n", style="yellow")
            result_text.append(f"Municipality Name: {result['municipality_name']}\n", style="green")
            result_text.append(f"Status: {result['message']}", style="green")
            
            if result.get('backup_file'):
                result_text.append(f"\n\nBackup created: {result['backup_file']}", style="dim")
            
            console.print(Panel(result_text, title="Update Municipality", border_style="green"))
            
    except Exception as e:
        _handle_json_error(e, json_out)
