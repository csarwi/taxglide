import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { theme } from '../theme';

interface AvailableYears {
  available_years: number[];
  count: number;
}

interface YearOperationResult {
  source_year?: number;
  target_year: number;
  success: boolean;
  message: string;
  archive_file?: string;
}

const YearManager: React.FC = () => {
  const [years, setYears] = useState<number[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Create year form state
  const [sourceYear, setSourceYear] = useState<number | null>(null);
  const [targetYear, setTargetYear] = useState<number>(new Date().getFullYear() + 1);
  const [overwrite, setOverwrite] = useState(false);

  useEffect(() => {
    loadYears();
  }, []);

  const loadYears = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result: AvailableYears = await invoke('list_years');
      setYears(result.available_years);
      
      // Set default source year to latest
      if (result.available_years.length > 0 && !sourceYear) {
        const latestYear = Math.max(...result.available_years);
        setSourceYear(latestYear);
        // Set target year to one year after latest
        if (!targetYear || targetYear <= latestYear) {
          setTargetYear(latestYear + 1);
        }
      }
    } catch (err) {
      setError(`Failed to load years: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateYear = async () => {
    if (!sourceYear) {
      setError('Please select a source year');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      const result: YearOperationResult = await invoke('create_year', {
        params: {
          source_year: sourceYear,
          target_year: targetYear,
          overwrite: overwrite ? true : undefined,
        }
      });

      if (result.success) {
        setSuccess(result.message);
        await loadYears(); // Refresh the list
        setTargetYear(targetYear + 1); // Increment for next time
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(`Failed to create year: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const clearMessages = () => {
    setError(null);
    setSuccess(null);
  };

  const buttonStyle = {
    padding: `${theme.spacing.sm} ${theme.spacing.md}`,
    border: `1px solid ${theme.colors.primary}`,
    borderRadius: theme.borderRadius.md,
    backgroundColor: theme.colors.primary,
    color: 'white',
    cursor: 'pointer',
    fontSize: theme.fontSizes.sm,
    fontWeight: '500',
    transition: 'all 0.2s ease',
  };

  const inputStyle = {
    padding: `${theme.spacing.sm} ${theme.spacing.md}`,
    border: `1px solid ${theme.colors.gray300}`,
    borderRadius: theme.borderRadius.md,
    fontSize: theme.fontSizes.sm,
    width: '120px',
  };

  const selectStyle = {
    ...inputStyle,
    width: '150px',
    backgroundColor: 'white',
  };

  return (
    <div>
      <h2 style={{
        fontSize: theme.fontSizes.xl,
        fontWeight: '600',
        color: theme.colors.text,
        margin: 0,
        marginBottom: theme.spacing.lg,
      }}>
        📅 Tax Year Management
      </h2>

      {/* Current Years */}
      <div style={{
        backgroundColor: theme.colors.backgroundSecondary,
        padding: theme.spacing.lg,
        borderRadius: theme.borderRadius.md,
        marginBottom: theme.spacing.xl,
        border: `1px solid ${theme.colors.gray200}`,
      }}>
        <h3 style={{
          fontSize: theme.fontSizes.lg,
          fontWeight: '500',
          margin: 0,
          marginBottom: theme.spacing.md,
          color: theme.colors.text,
        }}>
          Available Tax Years
        </h3>
        
        {loading && years.length === 0 ? (
          <p style={{ color: theme.colors.textSecondary }}>Loading years...</p>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: theme.spacing.sm }}>
            {years.length > 0 ? (
              years.map(year => (
                <span
                  key={year}
                  style={{
                    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                    backgroundColor: theme.colors.primary,
                    color: 'white',
                    borderRadius: theme.borderRadius.sm,
                    fontSize: theme.fontSizes.sm,
                    fontWeight: '500',
                  }}
                >
                  {year}
                </span>
              ))
            ) : (
              <p style={{ color: theme.colors.textSecondary }}>No tax years found</p>
            )}
          </div>
        )}
      </div>

      {/* Create New Year */}
      <div style={{
        backgroundColor: theme.colors.background,
        padding: theme.spacing.lg,
        borderRadius: theme.borderRadius.md,
        border: `1px solid ${theme.colors.gray200}`,
      }}>
        <h3 style={{
          fontSize: theme.fontSizes.lg,
          fontWeight: '500',
          margin: 0,
          marginBottom: theme.spacing.md,
          color: theme.colors.text,
        }}>
          Create New Tax Year
        </h3>
        
        <p style={{
          color: theme.colors.textSecondary,
          fontSize: theme.fontSizes.sm,
          marginBottom: theme.spacing.lg,
        }}>
          Copy configuration from an existing year to create a new tax year.
        </p>

        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: theme.spacing.md,
          marginBottom: theme.spacing.lg,
        }}>
          <div>
            <label style={{
              display: 'block',
              fontSize: theme.fontSizes.sm,
              fontWeight: '500',
              marginBottom: theme.spacing.xs,
              color: theme.colors.text,
            }}>
              Copy from year:
            </label>
            <select
              value={sourceYear || ''}
              onChange={(e) => setSourceYear(Number(e.target.value))}
              style={selectStyle}
            >
              <option value="">Select year...</option>
              {years.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>

          <div>
            <label style={{
              display: 'block',
              fontSize: theme.fontSizes.sm,
              fontWeight: '500',
              marginBottom: theme.spacing.xs,
              color: theme.colors.text,
            }}>
              Create year:
            </label>
            <input
              type="number"
              value={targetYear}
              onChange={(e) => setTargetYear(Number(e.target.value))}
              style={inputStyle}
              min="2020"
              max="2050"
            />
          </div>

          <div style={{ marginTop: '20px' }}>
            <label style={{
              display: 'flex',
              alignItems: 'center',
              fontSize: theme.fontSizes.sm,
              color: theme.colors.text,
              cursor: 'pointer',
            }}>
              <input
                type="checkbox"
                checked={overwrite}
                onChange={(e) => setOverwrite(e.target.checked)}
                style={{ marginRight: theme.spacing.xs }}
              />
              Overwrite if exists
            </label>
          </div>

          <div style={{ marginTop: '20px' }}>
            <button
              onClick={handleCreateYear}
              disabled={loading || !sourceYear}
              style={{
                ...buttonStyle,
                opacity: loading || !sourceYear ? 0.6 : 1,
                cursor: loading || !sourceYear ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Creating...' : 'Create Year'}
            </button>
          </div>
        </div>

        {/* Messages */}
        {(error || success) && (
          <div style={{
            padding: theme.spacing.md,
            borderRadius: theme.borderRadius.md,
            marginTop: theme.spacing.md,
            backgroundColor: error ? '#fee2e2' : '#dcfce7',
            border: `1px solid ${error ? '#fca5a5' : '#86efac'}`,
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'start',
            }}>
              <p style={{
                margin: 0,
                fontSize: theme.fontSizes.sm,
                color: error ? '#dc2626' : '#166534',
              }}>
                {error || success}
              </p>
              <button
                onClick={clearMessages}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: theme.fontSizes.lg,
                  color: error ? '#dc2626' : '#166534',
                  padding: 0,
                  lineHeight: 1,
                }}
              >
                ×
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default YearManager;