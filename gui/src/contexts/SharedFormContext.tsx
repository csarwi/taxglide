import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Shared form data that should be consistent across all views
export interface SharedFormData {
  year: number;
  income?: number;
  income_sg?: number;
  income_fed?: number;
  filing_status: string;
  pick: string[];
  skip: string[];
  max_deduction?: number;
}

interface SharedFormContextType {
  sharedData: SharedFormData;
  updateSharedData: (updates: Partial<SharedFormData>) => void;
  resetSharedData: () => void;
}

const defaultSharedData: SharedFormData = {
  year: 2025,
  filing_status: 'single', // Default to single
  pick: [],
  skip: [],
};

const SharedFormContext = createContext<SharedFormContextType | undefined>(undefined);

interface SharedFormProviderProps {
  children: ReactNode;
}

export const SharedFormProvider: React.FC<SharedFormProviderProps> = ({ children }) => {
  const [sharedData, setSharedData] = useState<SharedFormData>(defaultSharedData);

  // Load saved data from localStorage on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem('taxglide-shared-form-data');
      if (saved) {
        const parsedData = JSON.parse(saved);
        setSharedData({ ...defaultSharedData, ...parsedData });
      }
    } catch (error) {
      console.warn('Failed to load saved form data:', error);
    }
  }, []);

  // Save to localStorage whenever data changes
  useEffect(() => {
    try {
      localStorage.setItem('taxglide-shared-form-data', JSON.stringify(sharedData));
    } catch (error) {
      console.warn('Failed to save form data:', error);
    }
  }, [sharedData]);

  const updateSharedData = (updates: Partial<SharedFormData>) => {
    setSharedData(prev => ({ ...prev, ...updates }));
  };

  const resetSharedData = () => {
    setSharedData(defaultSharedData);
    localStorage.removeItem('taxglide-shared-form-data');
  };

  const value: SharedFormContextType = {
    sharedData,
    updateSharedData,
    resetSharedData,
  };

  return (
    <SharedFormContext.Provider value={value}>
      {children}
    </SharedFormContext.Provider>
  );
};

// Hook to use shared form context
export const useSharedForm = (): SharedFormContextType => {
  const context = useContext(SharedFormContext);
  if (context === undefined) {
    throw new Error('useSharedForm must be used within a SharedFormProvider');
  }
  return context;
};

export default SharedFormContext;
