import React, { useState, useEffect } from 'react';
import { invoke } from '@tauri-apps/api/core';
import { theme } from '../theme';

interface AvailableYears {
  available_years: number[];
  count: number;
}

interface Canton {
  name: string;
  key: string;
  municipalities: Municipality[];
}

interface Municipality {
  name: string;
  key: string;
}

interface AvailableLocations {
  cantons: Canton[];
  defaults: {
    canton: string;
    municipality: string;
  };
}

interface TaxMultiplier {
  name: string;
  code: string;
  kind: string;
  rate: number; // Always stored with 2 decimal places
  optional?: boolean;
  default_selected: boolean;
}

interface MunicipalityConfig {
  name: string;
  multipliers: Record<string, TaxMultiplier>;
  multiplier_order: string[];
}

const MunicipalityManager: React.FC = () => {
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [availableLocations, setAvailableLocations] = useState<AvailableLocations | null>(null);
  const [selectedCantonKey, setSelectedCantonKey] = useState<string>('');
  const [selectedMunicipalityKey, setSelectedMunicipalityKey] = useState<string>('');
  const [municipalityConfig, setMunicipalityConfig] = useState<MunicipalityConfig>({
    name: '',
    multipliers: {},
    multiplier_order: []
  });
  const [isEditing, setIsEditing] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadYears();
    loadLocations();
  }, []);

  useEffect(() => {
    if (selectedYear && selectedCantonKey && selectedMunicipalityKey && !isCreating) {
      loadMunicipalityConfig();
    }
  }, [selectedYear, selectedCantonKey, selectedMunicipalityKey, isCreating]);

  const loadYears = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result: AvailableYears = await invoke('list_years');
      setAvailableYears(result.available_years);
      
      if (result.available_years.length > 0 && !selectedYear) {
        setSelectedYear(Math.max(...result.available_years));
      }
    } catch (err) {
      setError(`Failed to load years: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const loadLocations = async () => {
    try {
      const result: AvailableLocations = await invoke('get_available_locations');
      setAvailableLocations(result);
      
      if (!selectedCantonKey && result.cantons.length > 0) {
        setSelectedCantonKey(result.cantons[0].key);
      }
    } catch (err) {
      setError(`Failed to load locations: ${err}`);
    }
  };

  const loadMunicipalityConfig = async () => {
    if (!selectedYear || !selectedCantonKey || !selectedMunicipalityKey) return;
    
    try {
      setLoading(true);
      setError(null);
      
      // Get canton details which includes municipality configurations
      const cantonData = await invoke('cli_get_canton', {
        year: selectedYear,
        cantonKey: selectedCantonKey
      });
      
      const parsedData = JSON.parse(cantonData as string);
      const municipality = parsedData.municipalities[selectedMunicipalityKey];
      
      if (municipality) {
        // Ensure all multipliers have the optional field properly set
        const sanitizedMunicipality = {
          ...municipality,
          multipliers: Object.fromEntries(
            Object.entries(municipality.multipliers).map(([key, multiplier]) => [
              key,
              {
                ...multiplier,
                optional: multiplier.optional ?? false
              }
            ])
          )
        };
        setMunicipalityConfig(sanitizedMunicipality);
      } else {
        setError(`Municipality ${selectedMunicipalityKey} not found`);
      }
    } catch (err) {
      setError(`Failed to load municipality config: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const startCreating = () => {
    setIsCreating(true);
    setIsEditing(true);
    setMunicipalityConfig({
      name: '',
      multipliers: {
        canton: {
          name: 'Kanton',
          code: 'KANTON',
          kind: 'factor',
          rate: 1.00,
          optional: false,
          default_selected: true
        },
        municipal: {
          name: 'Gemeinde',
          code: 'GEMEINDE',
          kind: 'factor',
          rate: 1.00,
          optional: false,
          default_selected: true
        }
      },
      multiplier_order: ['Kanton', 'Gemeinde']
    });
    setSelectedMunicipalityKey('');
  };

  const cancelEditing = () => {
    setIsCreating(false);
    setIsEditing(false);
    if (selectedMunicipalityKey) {
      loadMunicipalityConfig();
    } else {
      setMunicipalityConfig({ name: '', multipliers: {}, multiplier_order: [] });
    }
  };

  const addMultiplier = () => {
    const newKey = `multiplier_${Object.keys(municipalityConfig.multipliers).length + 1}`;
    const newMultiplier: TaxMultiplier = {
      name: 'New Multiplier',
      code: 'NEW',
      kind: 'factor',
      rate: 1.00,
      optional: false,
      default_selected: false
    };
    
    setMunicipalityConfig({
      ...municipalityConfig,
      multipliers: {
        ...municipalityConfig.multipliers,
        [newKey]: newMultiplier
      },
      multiplier_order: [...municipalityConfig.multiplier_order, newMultiplier.name]
    });
  };

  const updateMultiplier = (key: string, field: keyof TaxMultiplier, value: any) => {
    const updated = { ...municipalityConfig };
    const oldName = updated.multipliers[key].name;
    
    updated.multipliers[key] = { ...updated.multipliers[key], [field]: value };
    
    // Update multiplier_order if name changed
    if (field === 'name') {
      updated.multiplier_order = updated.multiplier_order.map(name => 
        name === oldName ? value : name
      );
    }
    
    setMunicipalityConfig(updated);
  };

  const removeMultiplier = (key: string) => {
    const updated = { ...municipalityConfig };
    const removedName = updated.multipliers[key].name;
    
    delete updated.multipliers[key];
    updated.multiplier_order = updated.multiplier_order.filter(name => name !== removedName);
    
    setMunicipalityConfig(updated);
  };

  const saveMunicipality = async () => {
    if (!selectedYear || !selectedCantonKey) {
      setError('Please select a year and canton');
      return;
    }
    
    if (!municipalityConfig.name) {
      setError('Please enter a municipality name');
      return;
    }
    
    const municipalityKey = selectedMunicipalityKey || municipalityConfig.name.toLowerCase().replace(/\s+/g, '_');
    
    // Sanitize municipality config to ensure proper boolean values
    const sanitizedConfig = {
      ...municipalityConfig,
      multipliers: Object.fromEntries(
        Object.entries(municipalityConfig.multipliers).map(([key, multiplier]) => [
          key,
          {
            ...multiplier,
            optional: Boolean(multiplier.optional),
            default_selected: Boolean(multiplier.default_selected)
          }
        ])
      )
    };
    
    try {
      setLoading(true);
      setError(null);
      setSuccess(null);

      if (isCreating) {
        await invoke('create_municipality', {
          params: {
            year: selectedYear,
            canton_key: selectedCantonKey,
            municipality_key: municipalityKey,
            municipality_config: sanitizedConfig,
          }
        });
        setSuccess('Municipality created successfully!');
        setSelectedMunicipalityKey(municipalityKey);
      } else {
        await invoke('update_municipality', {
          params: {
            year: selectedYear,
            canton_key: selectedCantonKey,
            municipality_key: selectedMunicipalityKey,
            municipality_config: sanitizedConfig,
          }
        });
        setSuccess('Municipality updated successfully!');
      }

      setIsCreating(false);
      setIsEditing(false);
      
      // Reload locations to reflect the new/updated municipality
      await loadLocations();
    } catch (err) {
      setError(`Failed to save municipality: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const selectedCanton = availableLocations?.cantons.find(c => c.key === selectedCantonKey);

  const inputStyle = {
    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
    border: `1px solid ${theme.colors.gray300}`,
    borderRadius: theme.borderRadius.sm,
    fontSize: theme.fontSizes.sm,
    width: '100%',
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
        🏙️ Municipality Manager
      </h2>

      {/* Year, Canton, and Municipality Selection */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: theme.spacing.md,
        marginBottom: theme.spacing.xl,
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
            style={{ ...inputStyle, backgroundColor: 'white' }}
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
            Canton:
          </label>
          <select
            value={selectedCantonKey}
            onChange={(e) => {
              setSelectedCantonKey(e.target.value);
              setSelectedMunicipalityKey('');
            }}
            style={{ ...inputStyle, backgroundColor: 'white' }}
          >
            <option value="">Select canton...</option>
            {availableLocations?.cantons.map(canton => (
              <option key={canton.key} value={canton.key}>{canton.name}</option>
            ))}
          </select>
        </div>

        {!isCreating && (
          <div>
            <label style={{
              display: 'block',
              fontSize: theme.fontSizes.sm,
              fontWeight: '500',
              marginBottom: theme.spacing.xs,
              color: theme.colors.text,
            }}>
              Municipality:
            </label>
            <select
              value={selectedMunicipalityKey}
              onChange={(e) => setSelectedMunicipalityKey(e.target.value)}
              style={{ ...inputStyle, backgroundColor: 'white' }}
            >
              <option value="">Select municipality...</option>
              {selectedCanton?.municipalities.map(municipality => (
                <option key={municipality.key} value={municipality.key}>{municipality.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div style={{
        display: 'flex',
        gap: theme.spacing.sm,
        marginBottom: theme.spacing.xl,
      }}>
        {!isEditing && (
          <>
            <button onClick={startCreating} style={buttonStyle}>
              + Create New Municipality
            </button>
            {selectedMunicipalityKey && (
              <button
                onClick={() => setIsEditing(true)}
                style={{
                  ...buttonStyle,
                  backgroundColor: theme.colors.secondary,
                  borderColor: theme.colors.secondary,
                }}
              >
                ✏️ Edit Municipality
              </button>
            )}
          </>
        )}

        {isEditing && (
          <>
            <button
              onClick={saveMunicipality}
              disabled={loading}
              style={{
                ...buttonStyle,
                opacity: loading ? 0.6 : 1,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Saving...' : (isCreating ? 'Create Municipality' : 'Save Changes')}
            </button>
            <button
              onClick={cancelEditing}
              style={{
                ...buttonStyle,
                backgroundColor: theme.colors.gray400,
                borderColor: theme.colors.gray400,
              }}
            >
              Cancel
            </button>
          </>
        )}

      </div>

      {/* Municipality Configuration Form */}
      {(isEditing || selectedMunicipalityKey) && (
        <div style={{
          backgroundColor: theme.colors.background,
          padding: theme.spacing.lg,
          borderRadius: theme.borderRadius.md,
          border: `1px solid ${theme.colors.gray200}`,
          marginBottom: theme.spacing.lg,
          position: 'relative',
        }}>
          <h3 style={{
            fontSize: theme.fontSizes.lg,
            fontWeight: '500',
            margin: 0,
            marginBottom: theme.spacing.md,
            color: theme.colors.text,
          }}>
            {isCreating ? 'New Municipality Configuration' : `${municipalityConfig.name} Configuration`}
          </h3>

          {/* Municipality Name */}
          <div style={{ marginBottom: theme.spacing.md }}>
            <label style={{
              display: 'block',
              fontSize: theme.fontSizes.sm,
              fontWeight: '500',
              marginBottom: theme.spacing.xs,
              color: theme.colors.text,
            }}>
              Municipality Name:
            </label>
            <input
              type="text"
              value={municipalityConfig.name}
              onChange={(e) => setMunicipalityConfig({
                ...municipalityConfig,
                name: e.target.value
              })}
              disabled={!isEditing}
              style={{
                ...inputStyle,
                backgroundColor: isEditing ? 'white' : theme.colors.gray100,
                cursor: isEditing ? 'text' : 'not-allowed',
              }}
              placeholder="Enter municipality name"
            />
          </div>

          {/* Tax Multipliers */}
          <div style={{ marginBottom: theme.spacing.md }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: theme.spacing.sm,
            }}>
              <label style={{
                fontSize: theme.fontSizes.sm,
                fontWeight: '500',
                color: theme.colors.text,
              }}>
                Tax Multipliers:
              </label>
              {isEditing && (
                <button onClick={addMultiplier} style={{
                  ...buttonStyle,
                  padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                  fontSize: theme.fontSizes.xs,
                }}>
                  + Add Multiplier
                </button>
              )}
            </div>

            {/* Header for multipliers grid */}
            {Object.keys(municipalityConfig.multipliers).length > 0 && (
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(150px, 1fr) minmax(100px, 1fr) 100px 90px 100px auto',
                gap: theme.spacing.sm,
                alignItems: 'center',
                padding: theme.spacing.sm,
                backgroundColor: theme.colors.gray100,
                borderRadius: theme.borderRadius.sm,
                marginBottom: theme.spacing.xs,
                fontSize: theme.fontSizes.xs,
                fontWeight: '600',
                color: theme.colors.textSecondary,
              }}>
                <div>Name</div>
                <div>Code</div>
                <div>Rate</div>
                <div>Optional</div>
                <div>Default</div>
                <div>Actions</div>
              </div>
            )}

            {Object.entries(municipalityConfig.multipliers).map(([key, multiplier]) => (
              <div key={key} style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(150px, 1fr) minmax(100px, 1fr) 100px 90px 100px auto',
                gap: theme.spacing.sm,
                alignItems: 'center',
                padding: theme.spacing.sm,
                backgroundColor: theme.colors.backgroundSecondary,
                borderRadius: theme.borderRadius.sm,
                marginBottom: theme.spacing.xs,
              }}>
                <input
                  type="text"
                  value={multiplier.name}
                  onChange={(e) => updateMultiplier(key, 'name', e.target.value)}
                  disabled={!isEditing}
                  style={{ 
                    ...inputStyle, 
                    fontSize: theme.fontSizes.xs, 
                    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                    backgroundColor: isEditing ? 'white' : theme.colors.gray100,
                  }}
                  placeholder="Name"
                />
                <input
                  type="text"
                  value={multiplier.code}
                  onChange={(e) => updateMultiplier(key, 'code', e.target.value)}
                  disabled={!isEditing}
                  style={{ 
                    ...inputStyle, 
                    fontSize: theme.fontSizes.xs, 
                    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                    backgroundColor: isEditing ? 'white' : theme.colors.gray100,
                  }}
                  placeholder="Code"
                />
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={multiplier.rate.toFixed(2)}
                  onChange={(e) => {
                    const value = parseFloat(e.target.value);
                    if (!isNaN(value)) {
                      updateMultiplier(key, 'rate', Math.round(value * 100) / 100);
                    }
                  }}
                  disabled={!isEditing}
                  style={{ 
                    ...inputStyle, 
                    fontSize: theme.fontSizes.xs, 
                    padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
                    backgroundColor: isEditing ? 'white' : theme.colors.gray100,
                  }}
                  placeholder="Rate"
                />
                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                }}>
                  <input
                    type="checkbox"
                    checked={multiplier.optional || false}
                    onChange={(e) => updateMultiplier(key, 'optional', e.target.checked)}
                    disabled={!isEditing}
                    style={{ cursor: isEditing ? 'pointer' : 'not-allowed' }}
                  />
                </div>
                <div style={{
                  display: 'flex',
                  justifyContent: 'center',
                  alignItems: 'center',
                }}>
                  <input
                    type="checkbox"
                    checked={multiplier.default_selected}
                    onChange={(e) => updateMultiplier(key, 'default_selected', e.target.checked)}
                    disabled={!isEditing}
                    style={{ cursor: isEditing ? 'pointer' : 'not-allowed' }}
                  />
                </div>
                {isEditing && (
                  <button
                    onClick={() => removeMultiplier(key)}
                    style={{
                      ...buttonStyle,
                      backgroundColor: '#ef4444',
                      borderColor: '#ef4444',
                      padding: `${theme.spacing.xs}`,
                      fontSize: theme.fontSizes.xs,
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Save Button - Always available when editing or viewing a municipality */}
          {(isEditing || selectedMunicipalityKey) && (
            <div style={{
              marginTop: theme.spacing.lg,
              paddingTop: theme.spacing.md,
              borderTop: `1px solid ${theme.colors.gray200}`,
              display: 'flex',
              justifyContent: 'flex-end',
              gap: theme.spacing.sm,
            }}>
              {isEditing ? (
                <>
                  <button
                    onClick={saveMunicipality}
                    disabled={loading}
                    style={{
                      ...buttonStyle,
                      backgroundColor: '#22c55e',
                      borderColor: '#22c55e',
                      opacity: loading ? 0.6 : 1,
                      cursor: loading ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {loading ? 'Saving...' : (isCreating ? '🎆 Create Municipality' : '💾 Save Changes')}
                  </button>
                  <button
                    onClick={cancelEditing}
                    style={{
                      ...buttonStyle,
                      backgroundColor: theme.colors.gray400,
                      borderColor: theme.colors.gray400,
                    }}
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setIsEditing(true)}
                  style={{
                    ...buttonStyle,
                    backgroundColor: theme.colors.secondary || '#3b82f6',
                    borderColor: theme.colors.secondary || '#3b82f6',
                  }}
                >
                  ✏️ Edit Municipality
                </button>
              )}
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
    </div>
  );
};

export default MunicipalityManager;