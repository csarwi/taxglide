import React, { useState } from 'react';
import { useCli, CalcParams, CalcResult } from '../contexts/CliContext';
import { theme, createButtonStyle, createCardStyle, createInputStyle } from '../theme';

// Helper function to extract Feuerwehr amount from warning message
const extractFeuerAmount = (warning: string): number | null => {
  const match = warning.match(/\+(\d+)\s+CHF/);
  return match ? parseInt(match[1]) : null;
};

const Calculator: React.FC = () => {
  const { calculate, isReady } = useCli();
  
  console.log('Calculator component rendering, isReady:', isReady);
  
  // Form state
  const [formData, setFormData] = useState<CalcParams>({
    year: 2025,
    filing_status: '',
    pick: [],
    skip: [],
  });
  
  const [result, setResult] = useState<CalcResult | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [useSeperateIncomes, setUseSeperateIncomes] = useState(false);

  // Handle form input changes
  const handleInputChange = (field: keyof CalcParams, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Handle calculation
  const handleCalculate = async () => {
    console.log('handleCalculate called, isReady:', isReady);
    
    if (!isReady) {
      const errorMsg = 'CLI is not ready. Please connect first.';
      console.log('Setting error:', errorMsg);
      setError(errorMsg);
      return;
    }

    try {
      console.log('Starting calculation...');
      setIsCalculating(true);
      setError(null);
      
      // Prepare parameters based on income mode
      const params: CalcParams = {
        ...formData,
        // Clear unused income fields
        ...(useSeperateIncomes ? {
          income: undefined,
        } : {
          income_sg: undefined,
          income_fed: undefined,
        })
      };

      console.log('Calculating with params:', params);
      const calcResult = await calculate(params);
      console.log('Calculation result:', calcResult);
      setResult(calcResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      console.error('Calculation error:', errorMessage);
      setError(errorMessage);
    } finally {
      console.log('Calculation finished');
      setIsCalculating(false);
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
          🧮 Tax Calculator
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
          handleCalculate();
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
                checked={useSeperateIncomes}
                onChange={(e) => setUseSeperateIncomes(e.target.checked)}
                style={{ marginRight: theme.spacing.sm }}
              />
              Use separate St. Gallen/Federal incomes
            </label>
          </div>

          {/* Income Inputs */}
          {useSeperateIncomes ? (
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
                required={!useSeperateIncomes}
              />
            </div>
          )}

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

          {/* Calculate Button */}
          <button
            type="submit"
            disabled={!isReady || isCalculating}
            style={{
              ...createButtonStyle('primary', !isReady || isCalculating),
              width: '100%',
              padding: `${theme.spacing.md} ${theme.spacing.lg}`,
              fontSize: theme.fontSizes.md,
              fontWeight: '600',
            }}
          >
            {isCalculating ? '⏳ Calculating...' : '🚀 Calculate Taxes'}
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
          📊 Tax Results
        </h3>

        {!result ? (
          <div style={{
            textAlign: 'center',
            padding: theme.spacing.xl,
            color: theme.colors.textSecondary,
            fontSize: theme.fontSizes.md,
          }}>
            Enter your information and click "Calculate Taxes" to see results.
          </div>
        ) : (
          <div>
            {/* Safety check to ensure we have valid result data */}
            {!result.total && !result.federal ? (
              <div style={{
                backgroundColor: theme.colors.statusWarning,
                border: `1px solid ${theme.colors.statusWarningBorder}`,
                borderRadius: theme.borderRadius.md,
                padding: theme.spacing.md,
                color: theme.colors.text,
              }}>
                ⚠️ Received incomplete calculation results. Please try again.
              </div>
            ) : (
              <>
                {/* Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: theme.spacing.md,
              marginBottom: theme.spacing.lg,
            }}>
              <div style={{
                backgroundColor: theme.colors.resultsBackground,
                padding: theme.spacing.md,
                borderRadius: theme.borderRadius.md,
                border: `1px solid ${theme.colors.resultsBorder}`,
              }}>
                <div style={{
                  fontSize: theme.fontSizes.xs,
                  color: theme.colors.resultsText,
                  marginBottom: theme.spacing.xs,
                }}>
                  Total Tax
                </div>
                <div style={{
                  fontSize: theme.fontSizes.xl,
                  fontWeight: '700',
                  color: theme.colors.resultsText,
                  fontFamily: theme.fonts.mono,
                }}>
                  CHF {result?.total?.toLocaleString() || '0'}
                </div>
              </div>

              <div style={{
                backgroundColor: theme.colors.statusSuccess,
                padding: theme.spacing.md,
                borderRadius: theme.borderRadius.md,
                border: `1px solid ${theme.colors.statusSuccessBorder}`,
              }}>
                <div style={{
                  fontSize: theme.fontSizes.xs,
                  color: theme.colors.text,
                  marginBottom: theme.spacing.xs,
                }}>
                  Effective Rate
                </div>
                <div style={{
                  fontSize: theme.fontSizes.xl,
                  fontWeight: '700',
                  color: theme.colors.text,
                  fontFamily: theme.fonts.mono,
                }}>
                  {((result?.avg_rate || 0) * 100).toFixed(2)}%
                </div>
              </div>
            </div>

            {/* Detailed Breakdown */}
            <div style={{
              backgroundColor: theme.colors.backgroundSecondary,
              padding: theme.spacing.md,
              borderRadius: theme.borderRadius.md,
              border: `1px solid ${theme.colors.gray200}`,
            }}>
              <h4 style={{
                margin: `0 0 ${theme.spacing.md} 0`,
                color: theme.colors.text,
                fontSize: theme.fontSizes.md,
              }}>
                💰 Tax Breakdown
              </h4>
              
              <div style={{ fontSize: theme.fontSizes.sm }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: theme.spacing.xs }}>
                  <span>Federal Income Tax:</span>
                  <span style={{ fontFamily: theme.fonts.mono }}>CHF {result?.federal?.toLocaleString() || '0'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: theme.spacing.xs }}>
                  <span>St. Gallen Income Tax:</span>
                  <span style={{ fontFamily: theme.fonts.mono }}>CHF {result?.sg_after_mult?.toLocaleString() || '0'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: theme.spacing.xs }}>
                  <span>St. Gallen Simple Tax:</span>
                  <span style={{ fontFamily: theme.fonts.mono }}>CHF {result?.sg_simple?.toLocaleString() || '0'}</span>
                </div>
              </div>
            </div>

            {/* Additional Tax Information */}
            {result.feuer_warning && (
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
                    const feuerAmount = extractFeuerAmount(result.feuer_warning || '');
                    if (feuerAmount) {
                      return `An additional Feuerwehr (Fire Department) tax of approximately CHF ${feuerAmount.toLocaleString()} may apply, depending on your municipality. This is not included in the calculation above.`;
                    }
                    return 'Additional Feuerwehr (Fire Department) tax may apply, depending on your municipality. This is not included in the calculation above.';
                  })()}
                </div>
              </div>
            )}
            </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Calculator;
