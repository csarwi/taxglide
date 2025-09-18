import React, { useState } from 'react';
import { useCli, OptimizeParams, OptimizeResult } from '../contexts/CliContext';
import { useSharedForm } from '../contexts/SharedFormContext';
import { theme, createButtonStyle, createCardStyle, createInputStyle } from '../theme';

// Helper function to extract Feuerwehr amount from warning message
const extractFeuerAmount = (warning: string): number | null => {
  const match = warning.match(/\+(\d+)\s+CHF/);
  return match ? parseInt(match[1]) : null;
};

const Optimizer: React.FC = () => {
  const { optimize, isReady } = useCli();
  const { sharedData, updateSharedData } = useSharedForm();
  
  // Local optimizer-specific state
  const [toleranceBp, setToleranceBp] = useState<number | undefined>();
  
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [showToleranceHelp, setShowToleranceHelp] = useState(false);

  // Handle form input changes
  const handleInputChange = (field: string, value: any) => {
    if (field === 'tolerance_bp') {
      setToleranceBp(value);
    } else {
      // Update shared form data for common fields
      updateSharedData({ [field]: value } as any);
    }
  };

  // Handle optimization
  const handleOptimize = async () => {
    if (!isReady) {
      const errorMsg = 'CLI is not ready. Please connect first.';
      setError(errorMsg);
      return;
    }

    try {
      setIsOptimizing(true);
      setError(null);
      
      // Prepare parameters based on income mode
      const params: OptimizeParams = {
        ...sharedData,
        tolerance_bp: toleranceBp,
        // Clear unused income fields
        ...(sharedData.useSeparateIncomes ? {
          income: undefined,
        } : {
          income_sg: undefined,
          income_fed: undefined,
        })
      };

      const optimizeResult = await optimize(params);
      setResult(optimizeResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setError(errorMessage);
    } finally {
      setIsOptimizing(false);
    }
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: window.innerWidth > 1024 ? '1fr 1fr' : '1fr',
      gap: theme.spacing.xl,
      alignItems: 'start',
      minHeight: '400px',
    }}>
      {/* Input Form */}
      <div style={createCardStyle()}>
        <h2 style={{
          marginTop: 0,
          marginBottom: theme.spacing.lg,
          color: theme.colors.primary,
          fontSize: theme.fontSizes.xl,
        }}>
          🎯 Tax Strategy Optimizer
        </h2>

        {error && (
          <div style={{
            backgroundColor: theme.colors.statusError,
            border: `1px solid ${theme.colors.statusErrorBorder}`,
            borderRadius: theme.borderRadius.md,
            padding: theme.spacing.md,
            marginBottom: theme.spacing.lg,
            color: theme.colors.text,
            fontSize: theme.fontSizes.sm,
          }}>
            <strong>❌ Error:</strong> {error}
          </div>
        )}

        <form onSubmit={(e) => {
          e.preventDefault();
          handleOptimize();
        }}>
          {/* Year Input */}
          <div style={{ marginBottom: theme.spacing.md }}>
            <label style={{
              display: 'block',
              marginBottom: theme.spacing.sm,
              fontWeight: '500',
              fontSize: theme.fontSizes.sm,
              color: theme.colors.text,
            }}>
              Tax Year
            </label>
            <input
              type="number"
              min="2020"
              max="2030"
              value={sharedData.year}
              onChange={(e) => handleInputChange('year', parseInt(e.target.value))}
              style={createInputStyle()}
              required
            />
          </div>

          {/* Income Mode Toggle */}
          <div style={{ marginBottom: theme.spacing.md }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              fontSize: theme.fontSizes.sm,
              color: theme.colors.text,
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={sharedData.useSeparateIncomes || false}
                onChange={(e) => handleInputChange('useSeparateIncomes', e.target.checked)}
                style={{ marginRight: theme.spacing.sm }}
              />
              Use separate Cantonal/Federal incomes
            </label>
          </div>

          {/* Income Inputs */}
          {sharedData.useSeparateIncomes ? (
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: theme.spacing.md,
              marginBottom: theme.spacing.md,
            }}>
              <div>
                <label style={{
                  display: 'block',
                  marginBottom: theme.spacing.sm,
                  fontWeight: '500',
                  fontSize: theme.fontSizes.sm,
                  color: theme.colors.text,
                }}>
                  Cantonal Income (CHF)
                </label>
                <input
                  type="number"
                  min="0"
                  value={sharedData.income_sg || ''}
                  onChange={(e) => handleInputChange('income_sg', e.target.value ? parseInt(e.target.value) : undefined)}
                  style={createInputStyle()}
                />
              </div>
              <div>
                <label style={{
                  display: 'block',
                  marginBottom: theme.spacing.sm,
                  fontWeight: '500',
                  fontSize: theme.fontSizes.sm,
                  color: theme.colors.text,
                }}>
                  Federal Income (CHF)
                </label>
                <input
                  type="number"
                  min="0"
                  value={sharedData.income_fed || ''}
                  onChange={(e) => handleInputChange('income_fed', e.target.value ? parseInt(e.target.value) : undefined)}
                  style={createInputStyle()}
                />
              </div>
            </div>
          ) : (
            <div style={{ marginBottom: theme.spacing.md }}>
              <label style={{
                display: 'block',
                marginBottom: theme.spacing.sm,
                fontWeight: '500',
                fontSize: theme.fontSizes.sm,
                color: theme.colors.text,
              }}>
                Total Income (CHF)
              </label>
              <input
                type="number"
                min="0"
                value={sharedData.income || ''}
                onChange={(e) => handleInputChange('income', e.target.value ? parseInt(e.target.value) : undefined)}
                style={createInputStyle()}
                required={!sharedData.useSeparateIncomes}
              />
            </div>
          )}

          {/* Max Deduction */}
          <div style={{ marginBottom: theme.spacing.md }}>
            <label style={{
              display: 'block',
              marginBottom: theme.spacing.sm,
              fontWeight: '500',
              fontSize: theme.fontSizes.sm,
              color: theme.colors.text,
            }}>
              Maximum Deduction (CHF)
            </label>
            <input
              type="number"
              min="0"
              value={sharedData.max_deduction || ''}
              onChange={(e) => handleInputChange('max_deduction', e.target.value ? parseInt(e.target.value) : undefined)}
              style={createInputStyle()}
              required
            />
          </div>

          {/* Filing Status */}
          <div style={{ marginBottom: theme.spacing.md }}>
            <label style={{
              display: 'block',
              marginBottom: theme.spacing.sm,
              fontWeight: '500',
              fontSize: theme.fontSizes.sm,
              color: theme.colors.text,
            }}>
              Filing Status (optional)
            </label>
            <select
              value={sharedData.filing_status || 'single'}
              onChange={(e) => handleInputChange('filing_status', e.target.value || 'single')}
              style={{
                ...createInputStyle(),
                cursor: 'pointer',
              }}
            >
              <option value="">-- Select Filing Status --</option>
              <option value="single">Single</option>
              <option value="married_joint">Married</option>
            </select>
          </div>

          {/* Advanced Options Toggle */}
          <div style={{ marginBottom: theme.spacing.md }}>
            <button
              type="button"
              onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              style={{
                background: 'none',
                border: 'none',
                color: theme.colors.primary,
                cursor: 'pointer',
                fontSize: theme.fontSizes.sm,
                padding: 0,
                textDecoration: 'underline',
                display: 'flex',
                alignItems: 'center',
                gap: theme.spacing.xs,
              }}
            >
              {showAdvancedOptions ? '🔼' : '🔽'} Advanced Options
            </button>
          </div>

          {/* Advanced Options Panel */}
          {showAdvancedOptions && (
            <div style={{
              backgroundColor: theme.colors.backgroundSecondary,
              border: `1px solid ${theme.colors.gray200}`,
              borderRadius: theme.borderRadius.md,
              padding: theme.spacing.md,
              marginBottom: theme.spacing.md,
            }}>
              <div style={{ marginBottom: theme.spacing.md }}>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: theme.spacing.sm,
                }}>
                  <label style={{
                    fontWeight: '500',
                    fontSize: theme.fontSizes.sm,
                    color: theme.colors.text,
                  }}>
                    ROI Tolerance (basis points)
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowToleranceHelp(!showToleranceHelp)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: theme.colors.primary,
                      cursor: 'pointer',
                      fontSize: theme.fontSizes.xs,
                      padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                      borderRadius: theme.borderRadius.sm,
                      textDecoration: 'none',
                    }}
                  >
                    {showToleranceHelp ? '❌ Hide Help' : '❓ What is this?'}
                  </button>
                </div>
                <input
                  type="number"
                  min="1"
                  max="500"
                  step="1"
                  value={toleranceBp || ''}
                  onChange={(e) => handleInputChange('tolerance_bp', e.target.value ? parseFloat(e.target.value) : undefined)}
                  placeholder="Auto (recommended)"
                  style={createInputStyle()}
                />
                <div style={{
                  fontSize: theme.fontSizes.xs,
                  color: theme.colors.textSecondary,
                  marginTop: theme.spacing.xs,
                }}>
                  Leave empty for automatic selection. Typical values: 10-50 basis points.
                  {toleranceBp && (
                    <span style={{ marginLeft: theme.spacing.xs }}>
                      (= {(toleranceBp / 100).toFixed(2)}%)
                    </span>
                  )}
                </div>

                {/* Expandable Help Section */}
                {showToleranceHelp && (
                  <div style={{
                    marginTop: theme.spacing.md,
                    padding: theme.spacing.md,
                    backgroundColor: 'rgba(59, 130, 246, 0.05)',
                    border: `1px solid rgba(59, 130, 246, 0.2)`,
                    borderRadius: theme.borderRadius.md,
                    fontSize: theme.fontSizes.sm,
                    lineHeight: '1.5',
                  }}>
                    <div style={{
                      fontWeight: '600',
                      color: theme.colors.text,
                      marginBottom: theme.spacing.sm,
                    }}>
                      🎯 Understanding ROI Tolerance
                    </div>
                    
                    <div style={{ marginBottom: theme.spacing.sm, color: theme.colors.text }}>
                      <strong>What it does:</strong> Controls how "picky" the optimizer is when finding your ideal deduction amount.
                    </div>
                    
                    <div style={{
                      marginBottom: theme.spacing.md,
                      padding: theme.spacing.sm,
                      backgroundColor: 'rgba(255, 193, 7, 0.1)',
                      borderLeft: `4px solid rgba(255, 193, 7, 0.5)`,
                      borderRadius: theme.borderRadius.sm,
                    }}>
                      <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.text }}>
                        🎯 How the "Sweet Spot" is Found:
                      </div>
                      <div style={{ color: theme.colors.textSecondary, fontSize: theme.fontSizes.sm }}>
                        <p style={{ marginBottom: theme.spacing.xs }}>
                          The optimizer first finds the deduction amount with the <strong>highest ROI</strong> (return on investment).
                        </p>
                        <p style={{ marginBottom: theme.spacing.xs }}>
                          Then it looks for a range of deductions where the ROI is within your tolerance of that maximum.
                        </p>
                        <p style={{ marginBottom: theme.spacing.xs }}>
                          <strong>Example:</strong> If the best ROI is 25.00% and your tolerance is 20 basis points (0.20%), 
                          the system will consider any deduction with ROI ≥ 24.80% as "good enough".
                        </p>
                        <p>
                          The "sweet spot" is chosen as the <strong>largest deduction</strong> in this "good enough" range, 
                          giving you maximum tax savings while staying near-optimal.
                        </p>
                      </div>
                    </div>
                    
                    <div style={{ marginBottom: theme.spacing.sm }}>
                      <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.text }}>
                        📊 Practical Examples:
                      </div>
                      <div style={{ color: theme.colors.textSecondary }}>
                        <div style={{ marginBottom: theme.spacing.sm, paddingLeft: theme.spacing.sm }}>
                          <strong style={{ color: theme.colors.text }}>10 basis points (0.10%):</strong><br/>
                          Very strict. If max ROI is 25%, only considers deductions with ROI ≥ 24.90%.<br/>
                          Result: Small, precise deduction amounts.
                        </div>
                        <div style={{ marginBottom: theme.spacing.sm, paddingLeft: theme.spacing.sm }}>
                          <strong style={{ color: theme.colors.text }}>50 basis points (0.50%):</strong><br/>
                          Balanced. If max ROI is 25%, considers deductions with ROI ≥ 24.50%.<br/>
                          Result: Moderate deduction range, good balance of ROI and savings.
                        </div>
                        <div style={{ paddingLeft: theme.spacing.sm }}>
                          <strong style={{ color: theme.colors.text }}>100 basis points (1.00%):</strong><br/>
                          Flexible. If max ROI is 25%, considers deductions with ROI ≥ 24.00%.<br/>
                          Result: Larger deductions, prioritizes maximum tax savings.
                        </div>
                      </div>
                    </div>
                    
                    <div style={{ marginBottom: theme.spacing.sm }}>
                      <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.text }}>
                        ⚙️ When to adjust:
                      </div>
                      <ul style={{ marginLeft: theme.spacing.md, color: theme.colors.textSecondary }}>
                        <li><strong>Use lower values (10-20)</strong>: If recommendations seem too aggressive</li>
                        <li><strong>Use higher values (50-100)</strong>: If recommendations seem too conservative</li>
                      </ul>
                    </div>
                    
                    <div style={{
                      padding: theme.spacing.sm,
                      backgroundColor: 'rgba(34, 197, 94, 0.1)',
                      borderRadius: theme.borderRadius.sm,
                      fontSize: theme.fontSizes.xs,
                      color: theme.colors.text,
                    }}>
                      💡 <strong>Recommendation:</strong> Leave this field empty for automatic selection. The system chooses conservative values based on your income level for practical multi-year tax planning.
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Optimize Button */}
          <button
            type="submit"
            disabled={!isReady || isOptimizing}
            style={{
              ...createButtonStyle('success', !isReady || isOptimizing),
              width: '100%',
              padding: `${theme.spacing.md} ${theme.spacing.lg}`,
              fontSize: theme.fontSizes.md,
              fontWeight: '600',
            }}
          >
            {isOptimizing ? '⏳ Optimizing...' : '🎯 Find Optimal Strategy'}
          </button>
        </form>
      </div>

      {/* Results Panel */}
      <div style={createCardStyle()}>
        <h3 style={{
          marginTop: 0,
          marginBottom: theme.spacing.lg,
          color: theme.colors.primary,
          fontSize: theme.fontSizes.xl,
        }}>
          📊 Optimization Results
        </h3>

        {!result ? (
          <div style={{
            textAlign: 'center',
            padding: theme.spacing.xl,
            color: theme.colors.textSecondary,
            fontSize: theme.fontSizes.md,
          }}>
            Enter your information and click "Find Optimal Strategy" to see recommendations.
          </div>
        ) : (
          <div>
            {/* Sweet Spot Recommendation */}
            <div style={{
              backgroundColor: theme.colors.statusSuccess,
              border: `2px solid ${theme.colors.statusSuccessBorder}`,
              borderRadius: theme.borderRadius.lg,
              padding: theme.spacing.lg,
              marginBottom: theme.spacing.lg,
            }}>
              <h4 style={{
                margin: `0 0 ${theme.spacing.md} 0`,
                color: theme.colors.text,
                fontSize: theme.fontSizes.lg,
                display: 'flex',
                alignItems: 'center',
                gap: theme.spacing.sm,
              }}>
                🎯 Sweet Spot Recommendation
              </h4>
              
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: theme.spacing.md,
                marginBottom: theme.spacing.md,
              }}>
                <div>
                  <div style={{
                    fontSize: theme.fontSizes.xs,
                    color: theme.colors.textSecondary,
                    marginBottom: theme.spacing.xs,
                  }}>
                    Optimal Deduction
                  </div>
                  <div style={{
                    fontSize: theme.fontSizes.xl,
                    fontWeight: '700',
                    color: theme.colors.text,
                    fontFamily: theme.fonts.mono,
                  }}>
                    CHF {result?.sweet_spot?.deduction?.toLocaleString() || '0'}
                  </div>
                </div>
                <div>
                  <div style={{
                    fontSize: theme.fontSizes.xs,
                    color: theme.colors.textSecondary,
                    marginBottom: theme.spacing.xs,
                  }}>
                    Tax Savings
                  </div>
                  <div style={{
                    fontSize: theme.fontSizes.xl,
                    fontWeight: '700',
                    color: theme.colors.success,
                    fontFamily: theme.fonts.mono,
                  }}>
                    CHF {result?.sweet_spot?.tax_saved_absolute?.toLocaleString() || '0'} ({(result?.sweet_spot?.tax_saved_percent || 0).toFixed(1)}%)
                  </div>
                </div>
              </div>
              
              <div style={{
                fontSize: theme.fontSizes.sm,
                color: theme.colors.text,
                backgroundColor: theme.colors.background,
                padding: theme.spacing.sm,
                borderRadius: theme.borderRadius.md,
                fontStyle: 'italic',
              }}>
                💡 {result?.sweet_spot?.explanation || 'No explanation available'}
              </div>
            </div>

            {/* ROI Analysis */}
            <div style={{
              backgroundColor: theme.colors.backgroundSecondary,
              padding: theme.spacing.md,
              borderRadius: theme.borderRadius.md,
              border: `1px solid ${theme.colors.gray200}`,
              marginBottom: theme.spacing.lg,
            }}>
              <h4 style={{
                margin: `0 0 ${theme.spacing.md} 0`,
                color: theme.colors.text,
                fontSize: theme.fontSizes.md,
              }}>
                📈 ROI Analysis
              </h4>
              
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: theme.spacing.sm,
                fontSize: theme.fontSizes.sm,
              }}>
                <div>
                  <div style={{ color: theme.colors.textSecondary, marginBottom: theme.spacing.xs }}>
                    Best ROI Rate
                  </div>
                  <div style={{ fontWeight: '600', fontFamily: theme.fonts.mono }}>
                    {(result?.best_rate?.savings_rate_percent || 0).toFixed(2)}%
                  </div>
                </div>
                <div>
                  <div style={{ color: theme.colors.textSecondary, marginBottom: theme.spacing.xs }}>
                    Plateau Range
                  </div>
                  <div style={{ fontWeight: '600', fontFamily: theme.fonts.mono }}>
                    CHF {result?.plateau_near_max_roi?.min_d?.toLocaleString() || '0'} - {result?.plateau_near_max_roi?.max_d?.toLocaleString() || '0'}
                  </div>
                </div>
                <div>
                  <div style={{ color: theme.colors.textSecondary, marginBottom: theme.spacing.xs }}>
                    Federal Bracket Changed
                  </div>
                  <div style={{ fontWeight: '600' }}>
                    {result?.sweet_spot?.optimization_summary?.federal_bracket_changed ? '✅ Yes' : '❌ No'}
                  </div>
                </div>
              </div>
            </div>

            {/* Tolerance Information */}
            {result?.tolerance_info && (
              <div style={{
                backgroundColor: theme.colors.backgroundSecondary,
                padding: theme.spacing.md,
                borderRadius: theme.borderRadius.md,
                border: `1px solid ${theme.colors.gray200}`,
                marginBottom: theme.spacing.lg,
              }}>
                <h4 style={{
                  margin: `0 0 ${theme.spacing.md} 0`,
                  color: theme.colors.text,
                  fontSize: theme.fontSizes.md,
                  display: 'flex',
                  alignItems: 'center',
                  gap: theme.spacing.xs,
                }}>
                  🎯 Optimization Tolerance
                </h4>
                
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: theme.spacing.sm,
                  fontSize: theme.fontSizes.sm,
                }}>
                  <div>
                    <div style={{ color: theme.colors.textSecondary, marginBottom: theme.spacing.xs }}>
                      Tolerance Used
                    </div>
                    <div style={{ fontWeight: '600', fontFamily: theme.fonts.mono }}>
                      {result.tolerance_info.tolerance_used_bp.toFixed(1)} bp ({(result.tolerance_info.tolerance_used_bp / 100).toFixed(2)}%)
                    </div>
                  </div>
                  <div>
                    <div style={{ color: theme.colors.textSecondary, marginBottom: theme.spacing.xs }}>
                      Selection Method
                    </div>
                    <div style={{ fontWeight: '600' }}>
                      {result.tolerance_info.tolerance_source === 'auto-selected' ? '🤖 Auto-selected' : '⚙️ Manual'}
                    </div>
                  </div>
                  <div>
                    <div style={{ color: theme.colors.textSecondary, marginBottom: theme.spacing.xs }}>
                      Optimization Type
                    </div>
                    <div style={{ fontWeight: '600' }}>
                      {result.adaptive_retry_used ? '🔄 Adaptive' : '📊 Standard'}
                    </div>
                  </div>
                </div>
                
                {result.adaptive_retry_used && (
                  <div style={{
                    marginTop: theme.spacing.md,
                    padding: theme.spacing.sm,
                    backgroundColor: 'rgba(168, 85, 247, 0.1)',
                    borderRadius: theme.borderRadius.sm,
                    fontSize: theme.fontSizes.xs,
                    lineHeight: '1.4',
                  }}>
                    <strong>🔄 Adaptive Optimization Applied:</strong> The system automatically retried with different tolerance settings and selected the result with the best balance of utilization and ROI ({result.adaptive_retry_used.selection_reason.replace('_', ' ')}).
                  </div>
                )}
              </div>
            )}

            {/* Tax Breakdown Comparison */}
            <div style={{
              backgroundColor: theme.colors.backgroundSecondary,
              padding: theme.spacing.md,
              borderRadius: theme.borderRadius.md,
              border: `1px solid ${theme.colors.gray200}`,
              marginBottom: theme.spacing.lg,
            }}>
              <h4 style={{
                margin: `0 0 ${theme.spacing.md} 0`,
                color: theme.colors.text,
                fontSize: theme.fontSizes.md,
              }}>
                💰 Before vs After Comparison
              </h4>
              
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: theme.spacing.md,
                fontSize: theme.fontSizes.sm,
              }}>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs }}>Tax Component</div>
                  <div style={{ marginBottom: theme.spacing.xs }}>Federal Tax:</div>
                  <div style={{ marginBottom: theme.spacing.xs }}>{result?.canton_name || 'Cantonal'} Tax:</div>
                  <div style={{ marginBottom: theme.spacing.xs, borderTop: `1px solid ${theme.colors.gray300}`, paddingTop: theme.spacing.xs, fontWeight: '600' }}>Total Tax:</div>
                </div>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.error }}>Before</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.baseline?.federal_tax?.toLocaleString() || '0'}</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.baseline?.sg_tax?.toLocaleString() || '0'}</div>
                  <div style={{ marginBottom: theme.spacing.xs, borderTop: `1px solid ${theme.colors.gray300}`, paddingTop: theme.spacing.xs, fontWeight: '600', fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.baseline?.total_tax?.toLocaleString() || '0'}</div>
                </div>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.success }}>After</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.federal_tax_at_spot?.toLocaleString() || '0'}</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.sg_tax_at_spot?.toLocaleString() || '0'}</div>
                  <div style={{ marginBottom: theme.spacing.xs, borderTop: `1px solid ${theme.colors.gray300}`, paddingTop: theme.spacing.xs, fontWeight: '600', fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.total_tax_at_spot?.toLocaleString() || '0'}</div>
                </div>
              </div>
            </div>

            {/* Income Details */}
            <div style={{
              backgroundColor: theme.colors.backgroundTertiary,
              padding: theme.spacing.md,
              borderRadius: theme.borderRadius.md,
              border: `1px solid ${theme.colors.gray200}`,
            }}>
              <h4 style={{
                margin: `0 0 ${theme.spacing.md} 0`,
                color: theme.colors.text,
                fontSize: theme.fontSizes.md,
              }}>
                📋 Income Details
              </h4>
              
              {sharedData.useSeparateIncomes ? (
                // Separate incomes case - show detailed breakdown
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: theme.spacing.md,
                  fontSize: theme.fontSizes.sm,
                }}>
                  <div>
                    <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs }}>Income Type</div>
                    <div style={{ marginBottom: theme.spacing.xs }}>{result?.canton_name || 'Cantonal'} Income:</div>
                    <div style={{ marginBottom: theme.spacing.xs }}>Federal Income:</div>
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.textSecondary }}>Original</div>
                    <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>
                      CHF {(sharedData.income_sg || 0).toLocaleString()}
                    </div>
                    <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>
                      CHF {(sharedData.income_fed || 0).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.success }}>After Deduction</div>
                    <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>
                      CHF {result?.sweet_spot?.income_details ? 
                        result.sweet_spot.income_details.after_deduction_sg?.toLocaleString() :
                        ((sharedData.income_sg || 0) - (result?.sweet_spot?.deduction || 0)).toLocaleString()
                      }
                    </div>
                    <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>
                      CHF {result?.sweet_spot?.income_details ? 
                        result.sweet_spot.income_details.after_deduction_fed?.toLocaleString() :
                        ((sharedData.income_fed || 0) - (result?.sweet_spot?.deduction || 0)).toLocaleString()
                      }
                    </div>
                  </div>
                </div>
              ) : (
                // Single income case - show simplified breakdown
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: theme.spacing.md,
                  fontSize: theme.fontSizes.sm,
                }}>
                  <div>
                    <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.textSecondary }}>Original Income</div>
                    <div style={{ fontFamily: theme.fonts.mono }}>CHF {(sharedData.income || 0).toLocaleString()}</div>
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.success }}>After Deduction</div>
                    <div style={{ fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.new_income?.toLocaleString() || '0'}</div>
                  </div>
                </div>
              )}
            </div>

            {/* Location Information */}
            {(result?.canton_name || result?.municipality_name) && (
              <div style={{
                backgroundColor: theme.colors.backgroundSecondary,
                border: `1px solid ${theme.colors.gray300}`,
                borderRadius: theme.borderRadius.md,
                padding: theme.spacing.md,
                marginTop: theme.spacing.md,
              }}>
                <h4 style={{
                  margin: `0 0 ${theme.spacing.sm} 0`,
                  color: theme.colors.text,
                  fontSize: theme.fontSizes.sm,
                  display: 'flex',
                  alignItems: 'center',
                  gap: theme.spacing.sm,
                }}>
                  📍 Location
                </h4>
                <div style={{
                  fontSize: theme.fontSizes.xs,
                  color: theme.colors.textSecondary,
                  lineHeight: '1.5',
                }}>
                  {result.canton_name && (
                    <div>Canton: <span style={{ fontWeight: '500', color: theme.colors.text }}>{result.canton_name}</span></div>
                  )}
                  {result.municipality_name && (
                    <div>Municipality: <span style={{ fontWeight: '500', color: theme.colors.text }}>{result.municipality_name}</span></div>
                  )}
                </div>
              </div>
            )}
            
            {/* Fire Department Tax Information */}
            {result?.sweet_spot?.multipliers?.feuer_warning && (
              <div style={{
                backgroundColor: theme.colors.backgroundSecondary,
                border: `1px solid ${theme.colors.gray300}`,
                borderRadius: theme.borderRadius.md,
                padding: theme.spacing.md,
                marginTop: theme.spacing.md,
              }}>
                <h4 style={{
                  margin: `0 0 ${theme.spacing.sm} 0`,
                  color: theme.colors.text,
                  fontSize: theme.fontSizes.sm,
                  display: 'flex',
                  alignItems: 'center',
                  gap: theme.spacing.sm,
                }}>
                  🚒 Additional Information
                </h4>
                <div style={{
                  fontSize: theme.fontSizes.xs,
                  color: theme.colors.textSecondary,
                  lineHeight: '1.5',
                }}>
                  {(() => {
                    const feuerAmount = extractFeuerAmount(result.sweet_spot.multipliers.feuer_warning || '');
                    if (feuerAmount) {
                      return `An additional Feuerwehr (Fire Department) tax of approximately CHF ${feuerAmount.toLocaleString()} may apply, depending on your municipality. This is not included in the optimization above.`;
                    }
                    return 'Additional Feuerwehr (Fire Department) tax may apply, depending on your municipality. This is not included in the optimization above.';
                  })()}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Optimizer;
