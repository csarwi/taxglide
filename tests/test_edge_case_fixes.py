#!/usr/bin/env python3
"""
Tests for edge case fixes.
"""

import pytest
from typer.testing import CliRunner
from taxglide.cli import app


def test_min_deduction_alignment():
    """Test that max_deduction < 100 fails fast with proper error message."""
    runner = CliRunner()
    
    # This should fail because max_deduction=50 < min_deduction=100
    result = runner.invoke(app, [
        "optimize", 
        "--year", "2025",
        "--income", "50000",
        "--max-deduction", "50"
    ])
    
    assert result.exit_code == 2
    assert "error" in result.stdout.lower()


def test_multiplier_display_formatting():
    """Test that multiplier displays show factor correctly (not as percent)."""
    runner = CliRunner()
    
    # Run optimization that should show multiplier factor info
    result = runner.invoke(app, [
        "optimize",
        "--year", "2025", 
        "--income", "50000",
        "--max-deduction", "5000"
    ])
    
    assert result.exit_code == 0
    # Should show "Total Factor: ×" not "Total Rate: ...%"
    assert "Total Factor: ×" in result.stdout
    assert "% of SG simple" in result.stdout


def test_filing_status_validation():
    """Test that invalid filing status fails with proper error message."""
    runner = CliRunner()
    
    result = runner.invoke(app, [
        "calc",
        "--year", "2025",
        "--income", "50000", 
        "--filing-status", "invalid"
    ])
    
    assert result.exit_code == 2
    # Error messages appear in stdout for CliRunner
    output = result.stdout + result.stderr if result.stderr else result.stdout
    # The exact message from our validator
    assert "Filing status must be one of:" in output or "married_joint, single" in output
    assert "married_joint" in output
    assert "single" in output


def test_negative_income_validation():
    """Test that negative incomes are rejected at CLI level."""
    runner = CliRunner()
    
    result = runner.invoke(app, [
        "calc", 
        "--year", "2025",
        "--income", "-1000"
    ])
    
    assert result.exit_code == 2
    # Typer should catch this with the min=0 constraint
