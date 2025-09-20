import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { theme } from '../theme';

interface ConfigSummary {
  year: number;
  schema_version: string;
  country: string;
  currency: string;
  canton_count: number;
  cantons: CantonSummary[];
  defaults: any;
  federal_filing_statuses: string[];
}

interface CantonSummary {
  key: string;
  name: string;
  abbreviation: string;
  bracket_count: number;
  municipality_count: number;
  municipalities: MunicipalitySummary[];
}

interface MunicipalitySummary {
  key: string;
  name: string;
  multiplier_count: number;
}

interface AvailableYears {
  available_years: number[];
  count: number;
}

const CantonManager: React.FC = () => {
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [config, setConfig] = useState<ConfigSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  // Modal state for editing
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingCanton, setEditingCanton] = useState<CantonSummary | null>(null);
  const [editForm, setEditForm] = useState({
    name: '',
    abbreviation: '',
    model: 'percent_of_bracket_portion',
    brackets: [] as Array<{ lower: number; width: number; rate_percent: number }>,
    rounding: {
      taxable_step: 1,
      tax_round_to: 0,
      scope: 'as_official'
    },
    override_config: null,
    notes: null,
    municipalities: {} as Record<string, any>
  });

  useEffect(() => {
    loadYears();
  }, []);
  
  useEffect(() => {
    if (selectedYear) {
      loadConfig();
    }
  }, [selectedYear]);

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
      
      const configData: ConfigSummary = await invoke('get_config_summary', {
        params: { year: selectedYear }
      });
      
      setConfig(configData);
    } catch (err) {
      setError(`Failed to load config: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCanton = async (cantonKey: string, cantonName: string) => {
    if (!selectedYear) {
      setError('Please select a year');
      return;
    }
    
    if (!window.confirm(`Are you sure you want to delete canton "${cantonName}"? This will permanently remove the canton and all its municipalities.`)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      await invoke('delete_canton', {
        params: {
          year: selectedYear,
          canton_key: cantonKey,
          confirm: true,
        }
      });

      setSuccess(`Canton "${cantonName}" deleted successfully`);
      await loadConfig(); // Refresh
    } catch (err) {
      setError(`Failed to delete canton: ${err}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleEditCanton = async (cantonKey: string, _cantonName: string) => {
    if (!config || !selectedYear) return;
    
    // Find the canton in our config
    const canton = config.cantons.find(c => c.key === cantonKey);
    if (!canton) return;
    
    setEditingCanton(canton);
    
    // Load full canton details for editing
    try {
      setLoading(true);
      const response = await invoke('cli_get_canton', {
        year: selectedYear,
        cantonKey: cantonKey
      });
      
      const cantonData = JSON.parse(response as string);
      setEditForm({
        name: cantonData.name,
        abbreviation: cantonData.abbreviation,
        model: 'percent_of_bracket_portion', // Always use this model
        brackets: cantonData.brackets,
        rounding: cantonData.rounding,
        override_config: null,
        notes: null,
        municipalities: cantonData.municipalities
      });
      setShowEditModal(true);
    } catch (error) {
      console.error('Failed to load canton details:', error);
      setError('Failed to load canton details for editing');
    } finally {
      setLoading(false);
    }
  };
  
  const handleSaveCanton = async () => {
    if (!editingCanton || !selectedYear) return;
    
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);
      
      // Call update_canton with the edited form data
      await invoke('update_canton', {
        params: {
          year: selectedYear,
          canton_key: editingCanton.key,
          canton_config: editForm
        }
      });
      
      setSuccess(`Canton "${editForm.name}" updated successfully`);
      setShowEditModal(false);
      setEditingCanton(null);
      
      // Refresh the config to show changes
      await loadConfig();
    } catch (error) {
      console.error('Failed to save canton:', error);
      setError(`Failed to save canton: ${error}`);
    } finally {
      setLoading(false);
    }
  };
  
  const handleCreateCanton = () => {
    if (!selectedYear) {
      setError('Please select a year first');
      return;
    }
    
    // TODO: Implement create canton modal/form
    // This would need to:
    // 1. Show modal with form for new canton
    // 2. Include fields for name, abbreviation, brackets, etc.
    // 3. Call create_canton on save
    alert(`Create New Canton for ${selectedYear} functionality coming soon!\n\nThis will allow you to:\n- Set canton name and abbreviation\n- Define tax brackets\n- Add municipalities\n- Configure rounding rules`);
  };

  const inputStyle = {
    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
    border: `1px solid ${theme.colors.gray300}`,
    borderRadius: theme.borderRadius.sm,
    fontSize: theme.fontSizes.sm,
    width: '120px',
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

  const dangerButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#ef4444',
    borderColor: '#ef4444',
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
        🏔️ Canton Management
      </h2>

      {/* Year Selection */}
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
        
        <div style={{ marginTop: '20px' }}>
          <button
            onClick={handleCreateCanton}
            style={buttonStyle}
          >
            + Add Canton
          </button>
        </div>
      </div>

      {/* Loading */}
      {loading && !config && (
        <div style={{
          textAlign: 'center',
          padding: theme.spacing.xl,
          color: theme.colors.textSecondary,
        }}>
          Loading configuration...
        </div>
      )}

      {/* Cantons List */}
      {config && (
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
            Available Cantons ({config.canton_count})
          </h3>

          {config.cantons.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: theme.spacing.xl,
              color: theme.colors.textSecondary,
              backgroundColor: theme.colors.backgroundSecondary,
              borderRadius: theme.borderRadius.md,
            }}>
              <p style={{ margin: 0 }}>No cantons found for {selectedYear}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: theme.spacing.md }}>
              {config.cantons.map((canton) => (
                <div
                  key={canton.key}
                  style={{
                    padding: theme.spacing.md,
                    border: `1px solid ${theme.colors.gray200}`,
                    borderRadius: theme.borderRadius.md,
                    backgroundColor: theme.colors.backgroundSecondary,
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'start',
                    marginBottom: theme.spacing.sm,
                  }}>
                    <div>
                      <h4 style={{
                        fontSize: theme.fontSizes.md,
                        fontWeight: '600',
                        margin: 0,
                        marginBottom: theme.spacing.xs,
                        color: theme.colors.text,
                      }}>
                        {canton.name} ({canton.abbreviation})
                      </h4>
                      <p style={{
                        fontSize: theme.fontSizes.sm,
                        color: theme.colors.textSecondary,
                        margin: 0,
                      }}>
                        Key: {canton.key}
                      </p>
                    </div>
                    
                    <div style={{ display: 'flex', gap: theme.spacing.xs }}>
                      <button
                        onClick={() => handleEditCanton(canton.key, canton.name)}
                        style={buttonStyle}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteCanton(canton.key, canton.name)}
                        disabled={loading}
                        style={{
                          ...dangerButtonStyle,
                          opacity: loading ? 0.6 : 1,
                          cursor: loading ? 'not-allowed' : 'pointer',
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>

                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                    gap: theme.spacing.sm,
                    fontSize: theme.fontSizes.sm,
                    color: theme.colors.textSecondary,
                  }}>
                    <div>📊 {canton.bracket_count} tax brackets</div>
                    <div>🏘️ {canton.municipality_count} municipalities</div>
                  </div>

                  {/* Municipalities */}
                  {canton.municipalities.length > 0 && (
                    <div style={{
                      marginTop: theme.spacing.md,
                      paddingTop: theme.spacing.md,
                      borderTop: `1px solid ${theme.colors.gray200}`,
                    }}>
                      <h5 style={{
                        fontSize: theme.fontSizes.sm,
                        fontWeight: '500',
                        margin: 0,
                        marginBottom: theme.spacing.xs,
                        color: theme.colors.text,
                      }}>
                        Municipalities:
                      </h5>
                      <div style={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: theme.spacing.xs,
                      }}>
                        {canton.municipalities.map((muni) => (
                          <span
                            key={muni.key}
                            style={{
                              padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                              backgroundColor: theme.colors.background,
                              border: `1px solid ${theme.colors.gray300}`,
                              borderRadius: theme.borderRadius.sm,
                              fontSize: theme.fontSizes.xs,
                              color: theme.colors.textSecondary,
                            }}
                          >
                            {muni.name} ({muni.multiplier_count} multipliers)
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
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
      
      {/* Edit Canton Modal */}
      {showEditModal && editingCanton && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: theme.colors.background,
            borderRadius: theme.borderRadius.lg,
            padding: theme.spacing.xl,
            maxWidth: '900px',
            width: '95%',
            maxHeight: '90vh',
            overflowY: 'auto',
            boxShadow: theme.shadows.lg,
          }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: theme.spacing.lg,
            }}>
              <h3 style={{
                fontSize: theme.fontSizes.xl,
                fontWeight: '600',
                margin: 0,
                color: theme.colors.text,
              }}>
                Edit Canton: {editingCanton.name}
              </h3>
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setEditingCanton(null);
                }}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: theme.fontSizes.xl,
                  cursor: 'pointer',
                  color: theme.colors.textSecondary,
                  padding: theme.spacing.xs,
                }}
              >
                ×
              </button>
            </div>
            
            {/* Form Content */}
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: theme.spacing.lg,
            }}>
              {/* Basic Details */}
              <div style={{
                padding: theme.spacing.md,
                backgroundColor: theme.colors.backgroundSecondary,
                borderRadius: theme.borderRadius.md,
              }}>
                <h4 style={{
                  fontSize: theme.fontSizes.md,
                  fontWeight: '500',
                  color: theme.colors.text,
                  marginBottom: theme.spacing.md,
                  margin: 0,
                }}>
                  📋 Basic Details
                </h4>
                
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: theme.spacing.md,
                  marginTop: theme.spacing.md,
                }}>
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: theme.fontSizes.sm,
                      fontWeight: '500',
                      marginBottom: theme.spacing.xs,
                      color: theme.colors.text,
                    }}>
                      Canton Name:
                    </label>
                    <input
                      type="text"
                      value={editForm.name}
                      onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                      style={{
                        ...inputStyle,
                        width: '100%',
                        backgroundColor: 'white',
                      }}
                      placeholder="Enter canton name"
                    />
                  </div>
                  
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: theme.fontSizes.sm,
                      fontWeight: '500',
                      marginBottom: theme.spacing.xs,
                      color: theme.colors.text,
                    }}>
                      Abbreviation:
                    </label>
                    <input
                      type="text"
                      value={editForm.abbreviation}
                      onChange={(e) => setEditForm({ ...editForm, abbreviation: e.target.value })}
                      style={{
                        ...inputStyle,
                        width: '100%',
                        backgroundColor: 'white',
                      }}
                      placeholder="Enter abbreviation"
                      maxLength={3}
                    />
                  </div>
                </div>
              </div>
              
              {/* Rounding Settings */}
              <div style={{
                padding: theme.spacing.md,
                backgroundColor: theme.colors.backgroundSecondary,
                borderRadius: theme.borderRadius.md,
              }}>
                <h4 style={{
                  fontSize: theme.fontSizes.md,
                  fontWeight: '500',
                  color: theme.colors.text,
                  marginBottom: theme.spacing.md,
                  margin: 0,
                }}>
                  ⚙️ Rounding Rules
                </h4>
                
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: theme.spacing.md,
                  marginTop: theme.spacing.md,
                }}>
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: theme.fontSizes.sm,
                      fontWeight: '500',
                      marginBottom: theme.spacing.xs,
                      color: theme.colors.text,
                    }}>
                      Taxable Step:
                    </label>
                    <input
                      type="number"
                      value={editForm.rounding.taxable_step}
                      onChange={(e) => setEditForm({ 
                        ...editForm, 
                        rounding: { ...editForm.rounding, taxable_step: parseInt(e.target.value) || 1 }
                      })}
                      style={{
                        ...inputStyle,
                        width: '100%',
                        backgroundColor: 'white',
                      }}
                      min="1"
                    />
                  </div>
                  
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: theme.fontSizes.sm,
                      fontWeight: '500',
                      marginBottom: theme.spacing.xs,
                      color: theme.colors.text,
                    }}>
                      Tax Round To:
                    </label>
                    <input
                      type="number"
                      value={editForm.rounding.tax_round_to}
                      onChange={(e) => setEditForm({ 
                        ...editForm, 
                        rounding: { ...editForm.rounding, tax_round_to: parseInt(e.target.value) || 0 }
                      })}
                      style={{
                        ...inputStyle,
                        width: '100%',
                        backgroundColor: 'white',
                      }}
                      min="0"
                    />
                  </div>
                  
                  <div>
                    <label style={{
                      display: 'block',
                      fontSize: theme.fontSizes.sm,
                      fontWeight: '500',
                      marginBottom: theme.spacing.xs,
                      color: theme.colors.text,
                    }}>
                      Scope:
                    </label>
                    <select
                      value={editForm.rounding.scope}
                      onChange={(e) => setEditForm({ 
                        ...editForm, 
                        rounding: { ...editForm.rounding, scope: e.target.value }
                      })}
                      style={{
                        ...inputStyle,
                        width: '100%',
                        backgroundColor: 'white',
                      }}
                    >
                      <option value="as_official">As Official</option>
                      <option value="both">Both</option>
                      <option value="taxable_only">Taxable Only</option>
                    </select>
                  </div>
                </div>
              </div>
              
              {/* Tax Brackets */}
              <div style={{
                padding: theme.spacing.md,
                backgroundColor: theme.colors.backgroundSecondary,
                borderRadius: theme.borderRadius.md,
              }}>
                <h4 style={{
                  fontSize: theme.fontSizes.md,
                  fontWeight: '500',
                  color: theme.colors.text,
                  marginBottom: theme.spacing.md,
                  margin: 0,
                }}>
                  📊 Tax Brackets ({editForm.brackets.length})
                </h4>
                
                <div style={{
                  marginTop: theme.spacing.md,
                  maxHeight: '200px',
                  overflowY: 'auto',
                  border: `1px solid ${theme.colors.gray200}`,
                  borderRadius: theme.borderRadius.sm,
                }}>
                  {editForm.brackets.map((bracket, index) => (
                    <div key={index} style={{
                      padding: theme.spacing.sm,
                      borderBottom: index < editForm.brackets.length - 1 ? `1px solid ${theme.colors.gray200}` : 'none',
                      backgroundColor: index % 2 === 0 ? 'white' : theme.colors.backgroundSecondary,
                      display: 'grid',
                      gridTemplateColumns: '1fr 1fr 1fr auto',
                      gap: theme.spacing.sm,
                      alignItems: 'center',
                    }}>              
                      <div>
                        <label style={{ fontSize: theme.fontSizes.xs, color: theme.colors.textSecondary }}>Lower:</label>
                        <input
                          type="number"
                          value={bracket.lower}
                          onChange={(e) => {
                            const newBrackets = [...editForm.brackets];
                            newBrackets[index] = { ...bracket, lower: parseInt(e.target.value) || 0 };
                            setEditForm({ ...editForm, brackets: newBrackets });
                          }}
                          style={{
                            fontSize: theme.fontSizes.xs,
                            padding: theme.spacing.xs,
                            border: `1px solid ${theme.colors.gray300}`,
                            borderRadius: theme.borderRadius.sm,
                            width: '100%',
                          }}
                        />
                      </div>
                      
                      <div>
                        <label style={{ fontSize: theme.fontSizes.xs, color: theme.colors.textSecondary }}>Width:</label>
                        <input
                          type="number"
                          value={bracket.width}
                          onChange={(e) => {
                            const newBrackets = [...editForm.brackets];
                            newBrackets[index] = { ...bracket, width: parseInt(e.target.value) || 0 };
                            setEditForm({ ...editForm, brackets: newBrackets });
                          }}
                          style={{
                            fontSize: theme.fontSizes.xs,
                            padding: theme.spacing.xs,
                            border: `1px solid ${theme.colors.gray300}`,
                            borderRadius: theme.borderRadius.sm,
                            width: '100%',
                          }}
                        />
                      </div>
                      
                      <div>
                        <label style={{ fontSize: theme.fontSizes.xs, color: theme.colors.textSecondary }}>Rate %:</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={bracket.rate_percent.toFixed(2)}
                          onChange={(e) => {
                            const value = parseFloat(e.target.value);
                            if (!isNaN(value)) {
                              const newBrackets = [...editForm.brackets];
                              newBrackets[index] = { ...bracket, rate_percent: Math.round(value * 100) / 100 };
                              setEditForm({ ...editForm, brackets: newBrackets });
                            }
                          }}
                          style={{
                            fontSize: theme.fontSizes.xs,
                            padding: theme.spacing.xs,
                            border: `1px solid ${theme.colors.gray300}`,
                            borderRadius: theme.borderRadius.sm,
                            width: '100%',
                          }}
                        />
                      </div>
                      
                      <button
                        onClick={() => {
                          const newBrackets = editForm.brackets.filter((_, i) => i !== index);
                          setEditForm({ ...editForm, brackets: newBrackets });
                        }}
                        style={{
                          background: '#ef4444',
                          color: 'white',
                          border: 'none',
                          borderRadius: theme.borderRadius.sm,
                          padding: theme.spacing.xs,
                          fontSize: theme.fontSizes.xs,
                          cursor: 'pointer',
                        }}
                        title="Delete bracket"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
                
                <button
                  onClick={() => {
                    const newBracket = { lower: 0, width: 10000, rate_percent: 1.00 };
                    setEditForm({ ...editForm, brackets: [...editForm.brackets, newBracket] });
                  }}
                  style={{
                    ...buttonStyle,
                    fontSize: theme.fontSizes.sm,
                    marginTop: theme.spacing.sm,
                    backgroundColor: theme.colors.gray400,
                    borderColor: theme.colors.gray400,
                  }}
                >
                  + Add Bracket
                </button>
              </div>
              
              {/* Municipalities & Multipliers */}
              <div style={{
                padding: theme.spacing.md,
                backgroundColor: theme.colors.backgroundSecondary,
                borderRadius: theme.borderRadius.md,
              }}>
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: theme.spacing.md,
                }}>
                  <h4 style={{
                    fontSize: theme.fontSizes.md,
                    fontWeight: '500',
                    color: theme.colors.text,
                    margin: 0,
                  }}>
                    🏘️ Municipalities & Tax Multipliers ({Object.keys(editForm.municipalities).length})
                  </h4>
                  
                  <div style={{
                    fontSize: theme.fontSizes.xs,
                    color: theme.colors.textSecondary,
                    textAlign: 'right',
                  }}>
                    📊 Multipliers are applied to base canton tax
                  </div>
                </div>
                
                {Object.keys(editForm.municipalities).length === 0 ? (
                  <div style={{
                    padding: theme.spacing.lg,
                    textAlign: 'center',
                    color: theme.colors.textSecondary,
                    fontStyle: 'italic',
                  }}>
                    No municipalities found. Add municipalities using the municipality management section.
                  </div>
                ) : (
                  <div style={{ marginTop: theme.spacing.md }}>
                    {Object.entries(editForm.municipalities).map(([muniKey, municipality]) => (
                      <div key={muniKey} style={{
                        marginBottom: theme.spacing.lg,
                        border: `1px solid ${theme.colors.gray200}`,
                        borderRadius: theme.borderRadius.md,
                        padding: theme.spacing.md,
                        backgroundColor: 'white',
                      }}>
                        <h5 style={{
                          fontSize: theme.fontSizes.sm,
                          fontWeight: '600',
                          color: theme.colors.text,
                          marginBottom: theme.spacing.md,
                          margin: 0,
                          display: 'flex',
                          alignItems: 'center',
                          gap: theme.spacing.sm,
                        }}>
                          <span>📍 {municipality.name}</span>
                          <span style={{ 
                            fontSize: theme.fontSizes.xs,
                            color: theme.colors.textSecondary,
                            fontWeight: 'normal',
                          }}>({muniKey})</span>
                        </h5>
                        
                        {/* Multipliers Grid */}
                        <div style={{
                          display: 'grid',
                          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                          gap: theme.spacing.sm,
                          marginTop: theme.spacing.md,
                        }}>
                          {Object.entries(municipality.multipliers).map(([multKey, multiplier]: [string, any]) => (
                            <div key={multKey} style={{
                              padding: theme.spacing.sm,
                              border: `1px solid ${theme.colors.gray300}`,
                              borderRadius: theme.borderRadius.sm,
                              backgroundColor: theme.colors.backgroundSecondary,
                            }}>
                              <div style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                marginBottom: theme.spacing.xs,
                              }}>
                                <label style={{
                                  fontSize: theme.fontSizes.xs,
                                  fontWeight: '500',
                                  color: theme.colors.text,
                                }}>
                                  {multiplier.name}
                                </label>
                                <span style={{
                                  fontSize: theme.fontSizes.xs,
                                  color: theme.colors.textSecondary,
                                  fontFamily: 'monospace',
                                }}>
                                  {multiplier.code}
                                </span>
                              </div>
                              
                              <div style={{
                                display: 'flex',
                                gap: theme.spacing.xs,
                                alignItems: 'center',
                              }}>
                                <input
                                  type="number"
                                  step="0.0001"
                                  value={multiplier.rate}
                                  onChange={(e) => {
                                    const newMunicipalities = { ...editForm.municipalities };
                                    newMunicipalities[muniKey].multipliers[multKey] = {
                                      ...multiplier,
                                      rate: parseFloat(e.target.value) || 0
                                    };
                                    setEditForm({ ...editForm, municipalities: newMunicipalities });
                                  }}
                                  style={{
                                    fontSize: theme.fontSizes.xs,
                                    padding: theme.spacing.xs,
                                    border: `1px solid ${theme.colors.gray300}`,
                                    borderRadius: theme.borderRadius.sm,
                                    width: '80px',
                                    backgroundColor: 'white',
                                  }}
                                />
                                <span style={{
                                  fontSize: theme.fontSizes.xs,
                                  color: theme.colors.textSecondary,
                                }}>×</span>
                                
                                <label style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  fontSize: theme.fontSizes.xs,
                                  color: theme.colors.textSecondary,
                                  cursor: 'pointer',
                                }}>
                                  <input
                                    type="checkbox"
                                    checked={multiplier.default_selected}
                                    onChange={(e) => {
                                      const newMunicipalities = { ...editForm.municipalities };
                                      newMunicipalities[muniKey].multipliers[multKey] = {
                                        ...multiplier,
                                        default_selected: e.target.checked
                                      };
                                      setEditForm({ ...editForm, municipalities: newMunicipalities });
                                    }}
                                    style={{
                                      width: '12px',
                                      height: '12px',
                                    }}
                                  />
                                  Default
                                </label>
                              </div>
                              
                              {multiplier.optional && (
                                <div style={{
                                  marginTop: theme.spacing.xs,
                                  fontSize: theme.fontSizes.xs,
                                  color: theme.colors.textSecondary,
                                  fontStyle: 'italic',
                                }}>
                                  Optional multiplier
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                        
                        {/* Municipality Summary */}
                        <div style={{
                          marginTop: theme.spacing.md,
                          padding: theme.spacing.xs,
                          backgroundColor: theme.colors.backgroundSecondary,
                          borderRadius: theme.borderRadius.sm,
                          fontSize: theme.fontSizes.xs,
                          color: theme.colors.textSecondary,
                          display: 'flex',
                          justifyContent: 'space-between',
                        }}>
                          <span>{Object.keys(municipality.multipliers).length} multipliers</span>
                          <span>
                            Default total: ×{(Object.values(municipality.multipliers as any) as any[])
                              .filter((m: any) => m.default_selected)
                              .reduce((sum, m: any) => sum + m.rate, 0)
                              .toFixed(4)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Overall Summary */}
              <div style={{
                padding: theme.spacing.md,
                backgroundColor: theme.colors.backgroundSecondary,
                borderRadius: theme.borderRadius.md,
                fontSize: theme.fontSizes.sm,
                color: theme.colors.textSecondary,
              }}>
                📄 <strong>Summary:</strong>{' '}
                {editForm.brackets.length} tax brackets,{' '}
                {Object.keys(editForm.municipalities).length} municipalities,{' '}
                {Object.values(editForm.municipalities).reduce((total, muni) => total + Object.keys(muni.multipliers).length, 0)} total multipliers
                <br />
                <small style={{ marginTop: theme.spacing.xs, display: 'block' }}>
                  Changes will be saved to the {selectedYear} tax configuration. All municipalities and their multipliers will be preserved.
                </small>
              </div>
              
              {/* Action Buttons */}
              <div style={{
                display: 'flex',
                gap: theme.spacing.sm,
                justifyContent: 'flex-end',
                paddingTop: theme.spacing.md,
                borderTop: `1px solid ${theme.colors.gray200}`,
              }}>
                <button
                  onClick={() => {
                    setShowEditModal(false);
                    setEditingCanton(null);
                  }}
                  style={{
                    ...buttonStyle,
                    backgroundColor: theme.colors.gray400,
                    borderColor: theme.colors.gray400,
                    padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                
                <button
                  onClick={handleSaveCanton}
                  style={{
                    ...buttonStyle,
                    padding: `${theme.spacing.sm} ${theme.spacing.lg}`,
                    opacity: loading ? 0.6 : 1,
                    cursor: loading ? 'not-allowed' : 'pointer',
                  }}
                  disabled={loading}
                >
                  {loading ? '💾 Saving...' : '💾 Save Changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CantonManager;