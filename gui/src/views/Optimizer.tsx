import React, { useState } from 'react';
import { useCli, OptimizeParams, OptimizeResult } from '../contexts/CliContext';
import { theme, createButtonStyle, createCardStyle, createInputStyle } from '../theme';

// Helper function to extract Feuerwehr amount from warning message
const extractFeuerAmount = (warning: string): number | null => {
  const match = warning.match(/\+(\d+)\s+CHF/);
  return match ? parseInt(match[1]) : null;
};

const Optimizer: React.FC = () => {
  const { optimize, isReady } = useCli();
  
  // Form state
  const [formData, setFormData] = useState<OptimizeParams>({
    year: 2025,
    filing_status: '',
    pick: [],
    skip: [],
  });
  
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useSeparateIncomes, setUseSeparateIncomes] = useState(false);

  // Handle form input changes
  const handleInputChange = (field: keyof OptimizeParams, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
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
        ...formData,
        // Clear unused income fields
        ...(useSeparateIncomes ? {
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
              value={formData.year}
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
                checked={useSeparateIncomes}
                onChange={(e) => setUseSeparateIncomes(e.target.checked)}
                style={{ marginRight: theme.spacing.sm }}
              />
              Use separate St. Gallen/Federal incomes
            </label>
          </div>

          {/* Income Inputs */}
          {useSeparateIncomes ? (
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
                  St. Gallen Income (CHF)
                </label>
                <input
                  type="number"
                  min="0"
                  value={formData.income_sg || ''}
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
                  value={formData.income_fed || ''}
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
                value={formData.income || ''}
                onChange={(e) => handleInputChange('income', e.target.value ? parseInt(e.target.value) : undefined)}
                style={createInputStyle()}
                required={!useSeparateIncomes}
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
              value={formData.max_deduction || ''}
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
              value={formData.filing_status || ''}
              onChange={(e) => handleInputChange('filing_status', e.target.value || undefined)}
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
                  <div style={{ marginBottom: theme.spacing.xs }}>St. Gallen Tax:</div>
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
              
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: theme.spacing.md,
                fontSize: theme.fontSizes.sm,
              }}>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs }}>Income Type</div>
                  <div style={{ marginBottom: theme.spacing.xs }}>St. Gallen Income:</div>
                  <div style={{ marginBottom: theme.spacing.xs }}>Federal Income:</div>
                </div>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.textSecondary }}>Original</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.income_details?.original_sg?.toLocaleString() || '0'}</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.income_details?.original_fed?.toLocaleString() || '0'}</div>
                </div>
                <div>
                  <div style={{ fontWeight: '600', marginBottom: theme.spacing.xs, color: theme.colors.success }}>After Deduction</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.income_details?.after_deduction_sg?.toLocaleString() || '0'}</div>
                  <div style={{ marginBottom: theme.spacing.xs, fontFamily: theme.fonts.mono }}>CHF {result?.sweet_spot?.income_details?.after_deduction_fed?.toLocaleString() || '0'}</div>
                </div>
              </div>
            </div>

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
