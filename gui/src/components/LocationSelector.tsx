import React, { useState, useEffect, useRef } from 'react';
import { useCli, AvailableLocations } from '../contexts/CliContext';
import { useSharedForm } from '../contexts/SharedFormContext';
import { theme, createInputStyle } from '../theme';

interface LocationSelectorProps {
  disabled?: boolean;
}

const LocationSelector: React.FC<LocationSelectorProps> = ({ disabled = false }) => {
  const { getAvailableLocations, isReady } = useCli();
  const { sharedData, updateSharedData } = useSharedForm();
  
  const [locations, setLocations] = useState<AvailableLocations | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Track if we've already loaded locations and set defaults to prevent unnecessary reloads
  const hasLoadedLocations = useRef(false);
  const hasSetDefaults = useRef(false);

  // Load available locations only once when CLI becomes ready
  useEffect(() => {
    const loadLocations = async () => {
      if (!isReady || hasLoadedLocations.current) return;
      
      try {
        setIsLoading(true);
        setError(null);
        const availableLocations = await getAvailableLocations();
        setLocations(availableLocations);
        hasLoadedLocations.current = true;
      } catch (err) {
        console.error('Failed to load locations:', err);
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setIsLoading(false);
      }
    };

    loadLocations();
  }, [isReady, getAvailableLocations]);

  // Set defaults only once after locations are loaded and if not already set
  useEffect(() => {
    if (!locations || hasSetDefaults.current) return;
    
    // Only set defaults if user hasn't already selected values
    if (!sharedData.canton && !sharedData.municipality) {
      updateSharedData({
        canton: locations.defaults.canton,
        municipality: locations.defaults.municipality,
      });
    }
    hasSetDefaults.current = true;
  }, [locations]); // Only depend on locations being loaded

  // Get municipalities for the selected canton
  const getAvailableMunicipalities = () => {
    if (!locations || !sharedData.canton) return [];
    
    const selectedCanton = locations.cantons.find(c => c.key === sharedData.canton);
    return selectedCanton ? selectedCanton.municipalities : [];
  };

  // Handle canton change
  const handleCantonChange = (cantonKey: string) => {
    const selectedCanton = locations?.cantons.find(c => c.key === cantonKey);
    if (!selectedCanton) return;

    // Reset municipality to first available in the new canton
    const firstMunicipality = selectedCanton.municipalities[0];
    updateSharedData({
      canton: cantonKey,
      municipality: firstMunicipality ? firstMunicipality.key : undefined,
    });
  };

  // Handle municipality change
  const handleMunicipalityChange = (municipalityKey: string) => {
    updateSharedData({ municipality: municipalityKey });
  };


  // Get municipalities for the selected canton
  const availableMunicipalities = getAvailableMunicipalities();

  return (
    <div>
      {/* Show error message if there's an error loading locations */}
      {error && (
        <div style={{
          backgroundColor: theme.colors.statusError,
          border: `1px solid ${theme.colors.statusErrorBorder}`,
          borderRadius: theme.borderRadius.md,
          padding: theme.spacing.sm,
          marginBottom: theme.spacing.md,
          color: theme.colors.text,
          fontSize: theme.fontSizes.xs,
        }}>
          <strong>❌ Error loading locations:</strong> {error}
        </div>
      )}
      
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: theme.spacing.md,
        marginBottom: theme.spacing.md,
      }}>
        {/* Canton Dropdown */}
        <div>
          <label style={{
            display: 'block',
            marginBottom: theme.spacing.sm,
            fontWeight: '500',
            fontSize: theme.fontSizes.sm,
            color: theme.colors.text,
          }}>
            Canton {isLoading && <span style={{ color: theme.colors.textSecondary, fontWeight: 'normal' }}>(⏳ Loading...)</span>}
          </label>
          <select
            value={sharedData.canton || ''}
            onChange={(e) => handleCantonChange(e.target.value)}
            disabled={disabled || isLoading}
            style={{
              ...createInputStyle(),
              cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.6 : isLoading ? 0.8 : 1,
            }}
          >
            {isLoading ? (
              <option value="">Loading cantons...</option>
            ) : error ? (
              <option value="">Error loading cantons</option>
            ) : !locations ? (
              <option value="">-- Select Canton --</option>
            ) : (
              <>
                <option value="">-- Select Canton --</option>
                {locations.cantons.map((canton) => (
                  <option key={canton.key} value={canton.key}>
                    {canton.name}
                  </option>
                ))}
              </>
            )}
          </select>
        </div>

        {/* Municipality Dropdown */}
        <div>
          <label style={{
            display: 'block',
            marginBottom: theme.spacing.sm,
            fontWeight: '500',
            fontSize: theme.fontSizes.sm,
            color: theme.colors.text,
          }}>
            Municipality {isLoading && <span style={{ color: theme.colors.textSecondary, fontWeight: 'normal' }}>(⏳ Loading...)</span>}
          </label>
          <select
            value={sharedData.municipality || ''}
            onChange={(e) => handleMunicipalityChange(e.target.value)}
            disabled={disabled || isLoading || !sharedData.canton}
            style={{
              ...createInputStyle(),
              cursor: disabled || isLoading || !sharedData.canton ? 'not-allowed' : 'pointer',
              opacity: disabled ? 0.6 : isLoading || !sharedData.canton ? 0.8 : 1,
            }}
          >
            {isLoading ? (
              <option value="">Loading municipalities...</option>
            ) : error ? (
              <option value="">Error loading municipalities</option>
            ) : !locations ? (
              <option value="">-- Select Municipality --</option>
            ) : !sharedData.canton ? (
              <option value="">Select canton first</option>
            ) : (
              <>
                <option value="">-- Select Municipality --</option>
                {availableMunicipalities.map((municipality) => (
                  <option key={municipality.key} value={municipality.key}>
                    {municipality.name}
                  </option>
                ))}
              </>
            )}
          </select>
        </div>
      </div>
    </div>
  );
};

export default LocationSelector;