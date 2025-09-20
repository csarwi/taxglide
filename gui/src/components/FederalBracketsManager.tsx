import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { theme } from '../theme';

// Remove unused interface

interface AvailableYears {
  available_years: number[];
  count: number;
}

interface FederalTaxSegment {
  from: number;
  to: number | null;
  at_income: number;
  base_tax_at: number;
  per100: number;
}

const FederalBracketsManager: React.FC = () => {
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [selectedStatus, setSelectedStatus] = useState<'single' | 'married_joint'>('single');
  const [segments, setSegments] = useState<FederalTaxSegment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadYears();
  }, []);
  
  useEffect(() => {
    if (selectedYear) {
      loadConfig();
    }
  }, [selectedYear, selectedStatus]);

  const loadYears = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result: AvailableYears = await invoke('list_years');
      setAvailableYears(result.available_years);
      
      // Set default year to latest
      if (result.available_years.length > 0 && !selectedYear) {
        setSelectedYear(Math.max(...result.available_years));
      }
    } catch (err) {
      setError(`Failed to load years: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const loadConfig = async () => {
    if (!selectedYear) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Load federal segments for the selected year and status
      const result = await invoke('get_federal_segments', {
        params: { 
          year: selectedYear, 
          filing_status: selectedStatus 
        }
      });
      
      // Convert segments to our local format
      const resultData = result as any;
      const loadedSegments: FederalTaxSegment[] = resultData.segments.map((seg: any) => ({
        from: seg.from,
        to: seg.to,
        at_income: seg.at_income,
        base_tax_at: seg.base_tax_at,
        per100: seg.per100
      }));
      
      setSegments(loadedSegments);
    } catch (err) {
      setError(`Failed to load federal segments: ${err}`);
      // Start with empty array if loading fails
      setSegments([]);
    } finally {
      setLoading(false);
    }
  };

  const addSegment = () => {
    const newSegment: FederalTaxSegment = {
      from: 0,
      to: null,
      at_income: 0,
      base_tax_at: 0,
      per100: 0,
    };
    setSegments([...segments, newSegment]);
  };

  const updateSegment = (index: number, field: keyof FederalTaxSegment, value: any) => {
    const updated = [...segments];
    updated[index] = { ...updated[index], [field]: value };
    setSegments(updated);
  };

  const removeSegment = (index: number) => {
    setSegments(segments.filter((_, i) => i !== index));
  };

  const saveSegments = async () => {
    if (!selectedYear) {
      setError('Please select a year');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      await invoke('update_federal_brackets', {
        params: {
          year: selectedYear,
          filing_status: selectedStatus,
          segments: segments,
        }
      });

      setSuccess('Federal brackets updated successfully!');
    } catch (err) {
      setError(`Failed to save segments: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const inputStyle = {
    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
    border: `1px solid ${theme.colors.gray300}`,
    borderRadius: theme.borderRadius.sm,
    fontSize: theme.fontSizes.sm,
    width: '100px',
  };

  const buttonStyle = {
    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
    border: `1px solid ${theme.colors.primary}`,
    borderRadius: theme.borderRadius.sm,
    backgroundColor: theme.colors.primary,
    color: 'white',
    cursor: 'pointer',
    fontSize: theme.fontSizes.sm,
    marginRight: theme.spacing.xs,
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
        🏛️ Federal Tax Brackets
      </h2>

      {/* Year and Filing Status Selection */}
      <div style={{
        display: 'flex',
        gap: theme.spacing.md,
        marginBottom: theme.spacing.xl,
        alignItems: 'center',
      }}>
        <div>
          <label style={{
            display: 'block',
            fontSize: theme.fontSizes.sm,
            fontWeight: '500',
            marginBottom: theme.spacing.xs,
            color: theme.colors.text,
          }}>
            Tax Year:
          </label>
          <select
            value={selectedYear || ''}
            onChange={(e) => setSelectedYear(e.target.value ? Number(e.target.value) : null)}
            style={{ ...inputStyle, width: '150px', backgroundColor: 'white' }}
          >
            <option value="">Select year...</option>
            {availableYears.map(year => (
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
            Filing Status:
          </label>
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value as 'single' | 'married_joint')}
            style={{ ...inputStyle, width: '150px', backgroundColor: 'white' }}
          >
            <option value="single">Single</option>
            <option value="married_joint">Married Joint</option>
          </select>
        </div>
      </div>

      {/* Segments Table */}
      <div style={{
        backgroundColor: theme.colors.background,
        padding: theme.spacing.lg,
        borderRadius: theme.borderRadius.md,
        border: `1px solid ${theme.colors.gray200}`,
        marginBottom: theme.spacing.lg,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: theme.spacing.md,
        }}>
          <h3 style={{
            fontSize: theme.fontSizes.lg,
            fontWeight: '500',
            margin: 0,
            color: theme.colors.text,
          }}>
            Tax Segments ({selectedStatus})
          </h3>
          <button onClick={addSegment} style={buttonStyle}>
            + Add Segment
          </button>
        </div>

        {segments.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: theme.spacing.xl,
            color: theme.colors.textSecondary,
            backgroundColor: theme.colors.backgroundSecondary,
            borderRadius: theme.borderRadius.md,
          }}>
            <p style={{ margin: 0, marginBottom: theme.spacing.sm }}>
              No segments configured yet
            </p>
            <p style={{ margin: 0, fontSize: theme.fontSizes.sm }}>
              Click "Add Segment" to start configuring federal tax brackets
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: theme.fontSizes.sm,
            }}>
              <thead>
                <tr style={{ backgroundColor: theme.colors.backgroundSecondary }}>
                  <th style={{ padding: theme.spacing.sm, textAlign: 'left', borderBottom: `1px solid ${theme.colors.gray200}` }}>From</th>
                  <th style={{ padding: theme.spacing.sm, textAlign: 'left', borderBottom: `1px solid ${theme.colors.gray200}` }}>To</th>
                  <th style={{ padding: theme.spacing.sm, textAlign: 'left', borderBottom: `1px solid ${theme.colors.gray200}` }}>At Income</th>
                  <th style={{ padding: theme.spacing.sm, textAlign: 'left', borderBottom: `1px solid ${theme.colors.gray200}` }}>Base Tax</th>
                  <th style={{ padding: theme.spacing.sm, textAlign: 'left', borderBottom: `1px solid ${theme.colors.gray200}` }}>Per 100</th>
                  <th style={{ padding: theme.spacing.sm, textAlign: 'left', borderBottom: `1px solid ${theme.colors.gray200}` }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {segments.map((segment, index) => (
                  <tr key={index}>
                    <td style={{ padding: theme.spacing.sm, borderBottom: `1px solid ${theme.colors.gray200}` }}>
                      <input
                        type="number"
                        value={segment.from}
                        onChange={(e) => updateSegment(index, 'from', Number(e.target.value))}
                        style={inputStyle}
                      />
                    </td>
                    <td style={{ padding: theme.spacing.sm, borderBottom: `1px solid ${theme.colors.gray200}` }}>
                      <input
                        type="number"
                        value={segment.to || ''}
                        onChange={(e) => updateSegment(index, 'to', e.target.value ? Number(e.target.value) : null)}
                        style={inputStyle}
                        placeholder="null"
                      />
                    </td>
                    <td style={{ padding: theme.spacing.sm, borderBottom: `1px solid ${theme.colors.gray200}` }}>
                      <input
                        type="number"
                        value={segment.at_income}
                        onChange={(e) => updateSegment(index, 'at_income', Number(e.target.value))}
                        style={inputStyle}
                      />
                    </td>
                    <td style={{ padding: theme.spacing.sm, borderBottom: `1px solid ${theme.colors.gray200}` }}>
                      <input
                        type="number"
                        step="0.01"
                        value={segment.base_tax_at}
                        onChange={(e) => updateSegment(index, 'base_tax_at', Number(e.target.value))}
                        style={inputStyle}
                      />
                    </td>
                    <td style={{ padding: theme.spacing.sm, borderBottom: `1px solid ${theme.colors.gray200}` }}>
                      <input
                        type="number"
                        step="0.01"
                        value={segment.per100}
                        onChange={(e) => updateSegment(index, 'per100', Number(e.target.value))}
                        style={inputStyle}
                      />
                    </td>
                    <td style={{ padding: theme.spacing.sm, borderBottom: `1px solid ${theme.colors.gray200}` }}>
                      <button
                        onClick={() => removeSegment(index)}
                        style={{
                          ...buttonStyle,
                          backgroundColor: '#ef4444',
                          borderColor: '#ef4444',
                        }}
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Save Button */}
      {segments.length > 0 && (
        <div style={{ textAlign: 'right' }}>
          <button
            onClick={saveSegments}
            disabled={loading}
            style={{
              ...buttonStyle,
              padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
              fontSize: theme.fontSizes.md,
              opacity: loading ? 0.6 : 1,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Saving...' : 'Save Federal Brackets'}
          </button>
        </div>
      )}

      {/* Messages */}
      {(error || success) && (
        <div style={{
          padding: theme.spacing.md,
          borderRadius: theme.borderRadius.md,
          marginTop: theme.spacing.md,
          backgroundColor: error ? '#fee2e2' : '#dcfce7',
          border: `1px solid ${error ? '#fca5a5' : '#86efac'}`,
        }}>
          <p style={{
            margin: 0,
            fontSize: theme.fontSizes.sm,
            color: error ? '#dc2626' : '#166534',
          }}>
            {error || success}
          </p>
        </div>
      )}
    </div>
  );
};

export default FederalBracketsManager;