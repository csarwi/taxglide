import React, { useState } from 'react';
import { useCli, ScanParams, ScanResult, ScanResultRow } from '../contexts/CliContext';
import { useSharedForm } from '../contexts/SharedFormContext';
import { createCardStyle, createButtonStyle, createInputStyle, theme } from '../theme';
import DataTable, { TableColumn } from '../components/DataTable';

// Helper function to format currency
const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('de-CH', {
    style: 'currency',
    currency: 'CHF',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
};

// Helper function to format percentage
const formatPercentage = (value: number): string => {
  return `${value.toFixed(2)}%`;
};

// Helper function to format federal bracket info

const Scanner: React.FC = () => {
  const { scan, isReady } = useCli();
  const { sharedData, updateSharedData } = useSharedForm();
  
  // Local scanner-specific state
  const [dStep, setDStep] = useState<number>(1000);
  const [includeMarginal, setIncludeMarginal] = useState<boolean>(true);
  
  const [result, setResult] = useState<ScanResult | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle form input changes
  const handleInputChange = (field: string, value: any) => {
    if (field === 'd_step') {
      setDStep(value);
    } else if (field === 'include_local_marginal') {
      setIncludeMarginal(value);
    } else {
      // Update shared form data for common fields
      updateSharedData({ [field]: value } as any);
    }
  };

  // Handle scan
  const handleScan = async () => {
    if (!isReady) {
      setError('CLI is not ready. Please connect first.');
      return;
    }

    try {
      setIsScanning(true);
      setError(null);
      
      // Prepare parameters based on income mode
      const params: ScanParams = {
        ...sharedData,
        max_deduction: sharedData.max_deduction || 50000, // Provide default if not set
        d_step: dStep,
        include_local_marginal: includeMarginal,
        // Clear unused income fields
        ...(sharedData.useSeparateIncomes ? {
          income: undefined,
        } : {
          income_sg: undefined,
          income_fed: undefined,
        })
      };

      console.log('Scanning with params:', params);
      const scanResult = await scan(params);
      console.log('Scan result:', scanResult);
      setResult(scanResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      console.error('Scan error:', errorMessage);
      setError(errorMessage);
    } finally {
      setIsScanning(false);
    }
  };

  // Define table columns
  const columns: TableColumn<ScanResultRow>[] = [
    {
      key: 'deduction',
      label: 'Deduction',
      sortable: true,
      align: 'right',
      width: '100px',
      render: (value: number) => formatCurrency(value),
    },
    {
      key: 'new_income',
      label: 'New Income',
      sortable: true,
      align: 'right',
      width: '120px',
      render: (value: number) => formatCurrency(value),
    },
    {
      key: 'total_tax',
      label: 'Total Tax',
      sortable: true,
      align: 'right',
      width: '100px',
      render: (value: number) => formatCurrency(value),
    },
    {
      key: 'saved',
      label: 'Tax Saved',
      sortable: true,
      align: 'right',
      width: '100px',
      render: (value: number) => {
        const color = value > 0 ? theme.colors.success : value < 0 ? theme.colors.error : theme.colors.textSecondary;
        return (
          <span style={{ color, fontWeight: value !== 0 ? '600' : 'normal' }}>
            {formatCurrency(value)}
          </span>
        );
      },
    },
    {
      key: 'roi_percent',
      label: 'ROI',
      sortable: true,
      align: 'right',
      width: '80px',
      render: (value: number) => {
        const color = value > 20 ? theme.colors.success : 
                     value > 10 ? theme.colors.warning : 
                     value > 0 ? theme.colors.textSecondary : theme.colors.error;
        return (
          <span style={{ color, fontWeight: '600' }}>
            {formatPercentage(value)}
          </span>
        );
      },
    },
    {
      key: 'federal',
      label: 'Federal Tax',
      sortable: true,
      align: 'right',
      width: '100px',
      render: (value: number) => formatCurrency(value),
    },
    {
      key: 'sg_after_multipliers',
      label: 'SG Tax',
      sortable: true,
      align: 'right',
      width: '100px',
      render: (value: number) => formatCurrency(value),
    },
    {
      key: 'federal_per100',
      label: 'Fed Rate',
      sortable: true,
      filterable: true,
      align: 'right',
      width: '80px',
      render: (value: number) => formatPercentage(value),
    },
  ];

  // Add marginal tax rate column if enabled
  if (includeMarginal) {
    columns.push({
      key: 'local_marginal_percent',
      label: 'Marginal Rate',
      sortable: true,
      align: 'right',
      width: '100px',
      render: (value: number | null) => {
        if (value === null) return '—';
        const color = value > 30 ? theme.colors.error : 
                     value > 20 ? theme.colors.warning : 
                     theme.colors.textSecondary;
        return (
          <span style={{ color, fontWeight: '600' }}>
            {formatPercentage(value)}
          </span>
        );
      },
    });
  }

  // Add separate income columns if different incomes are used
  if (sharedData.useSeparateIncomes && result && result.length > 0 && result[0].new_income_sg !== undefined) {
    // Insert SG and Federal income columns after new_income
    const incomeIndex = columns.findIndex(col => col.key === 'new_income');
    columns.splice(incomeIndex + 1, 0, 
      {
        key: 'new_income_sg',
        label: 'SG Income',
        sortable: true,
        align: 'right',
        width: '100px',
        render: (value: number | undefined) => value ? formatCurrency(value) : '—',
      },
      {
        key: 'new_income_fed',
        label: 'Fed Income',
        sortable: true,
        align: 'right',
        width: '100px',
        render: (value: number | undefined) => value ? formatCurrency(value) : '—',
      }
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: theme.spacing.xl,
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
          🔍 Deduction Scanner
        </h2>
        
        <p style={{
          marginBottom: theme.spacing.lg,
          color: theme.colors.textSecondary,
          fontSize: theme.fontSizes.sm,
        }}>
          Scan through different deduction amounts to see how they affect your taxes. 
          Results will be displayed in an interactive table below.
        </p>

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
          handleScan();
        }}>
          {/* First row: Year and Max Deduction */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
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
            
            <div>
              <label style={{
                display: 'block',
                marginBottom: theme.spacing.sm,
                fontWeight: '500',
                fontSize: theme.fontSizes.sm,
                color: theme.colors.text,
              }}>
                Max Deduction (CHF)
              </label>
              <input
                type="number"
                min="0"
                step="1000"
                value={sharedData.max_deduction || 50000}
                onChange={(e) => handleInputChange('max_deduction', parseInt(e.target.value))}
                style={createInputStyle()}
                required
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
                Step Size (CHF)
              </label>
              <input
                type="number"
                min="100"
                step="100"
                value={dStep || 1000}
                onChange={(e) => handleInputChange('d_step', parseInt(e.target.value))}
                style={createInputStyle()}
              />
            </div>
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
                required
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
                required
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

          {/* Advanced Options */}
          <div style={{ marginBottom: theme.spacing.lg }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              fontSize: theme.fontSizes.sm,
              color: theme.colors.text,
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={includeMarginal || false}
                onChange={(e) => handleInputChange('include_local_marginal', e.target.checked)}
                style={{ marginRight: theme.spacing.sm }}
              />
              Include marginal tax rate calculation (slower but more detailed)
            </label>
          </div>

          {/* Scan Button */}
          <button
            type="submit"
            disabled={!isReady || isScanning}
            style={{
              ...createButtonStyle('primary', !isReady || isScanning),
              width: '100%',
              padding: `${theme.spacing.md} ${theme.spacing.lg}`,
              fontSize: theme.fontSizes.md,
              fontWeight: '600',
            }}
          >
            {isScanning ? '⏳ Scanning...' : '🔍 Start Scan'}
          </button>
        </form>
      </div>

      {/* Results Panel */}
      {result && result.length > 0 && (
        <div style={createCardStyle()}>
          <h3 style={{
            marginTop: 0,
            marginBottom: theme.spacing.lg,
            color: theme.colors.primary,
            fontSize: theme.fontSizes.xl,
          }}>
            📊 Scan Results
          </h3>
          
          <p style={{
            marginBottom: theme.spacing.md,
            color: theme.colors.textSecondary,
            fontSize: theme.fontSizes.sm,
          }}>
            Interactive table showing tax calculations for different deduction amounts. 
            Click column headers to sort, use the search box to filter, or use column filters.
          </p>

          <DataTable
            data={result}
            columns={columns}
            searchPlaceholder="Search deduction amounts, taxes, ROI..."
            maxHeight="70vh"
          />
        </div>
      )}
      
      {!result && !isScanning && (
        <div style={{
          ...createCardStyle(),
          textAlign: 'center',
          padding: theme.spacing.xl,
          color: theme.colors.textSecondary,
          fontSize: theme.fontSizes.md,
        }}>
          Enter your scan parameters above and click "Start Scan" to see detailed results.
        </div>
      )}
    </div>
  );
};

export default Scanner;
