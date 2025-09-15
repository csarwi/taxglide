import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { invoke } from '@tauri-apps/api/core';

// Types (extracted from our previous CLI integration)
export interface VersionInfo {
  version: string;
  schema_version: string;
  build_timestamp: string;
  build_date: string;
  platform: string;
  supported_years: number[];
}

export interface CliStatusInfo {
  initialized: boolean;
  version_info: VersionInfo | null;
  error: string | null;
}

export interface CalcParams {
  year: number;
  income?: number;
  income_sg?: number;
  income_fed?: number;
  filing_status?: string;
  pick: string[];
  skip: string[];
}

export interface CalcResult {
  year: number;
  total_income: number;
  total_tax: number;
  effective_rate: number;
  marginal_rate: number;
  taxes: {
    federal_income: number;
    singapore_income: number;
    us_social_security: number;
    us_medicare: number;
    singapore_cpf: number;
  };
  warnings: string[];
  multipliers_applied: string[];
}

// Context type
interface CliContextType {
  status: CliStatusInfo | null;
  isInitializing: boolean;
  error: string | null;
  initializeCli: () => Promise<void>;
  calculate: (params: CalcParams) => Promise<CalcResult>;
  isReady: boolean;
}

const CliContext = createContext<CliContextType | undefined>(undefined);

interface CliProviderProps {
  children: ReactNode;
}

export const CliProvider: React.FC<CliProviderProps> = ({ children }) => {
  const [status, setStatus] = useState<CliStatusInfo | null>(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check if CLI is ready
  const isReady = status?.initialized === true && !error;

  // Initialize CLI connection
  const initializeCli = async () => {
    try {
      setIsInitializing(true);
      setError(null);
      
      console.log('Initializing CLI connection...');
      const versionInfo: VersionInfo = await invoke('init_cli');
      
      setStatus({
        initialized: true,
        version_info: versionInfo,
        error: null,
      });
      
      console.log('CLI initialized successfully:', versionInfo);
    } catch (err) {
      const errorMessage = err as string;
      console.error('CLI initialization failed:', errorMessage);
      
      setError(errorMessage);
      setStatus({
        initialized: false,
        version_info: null,
        error: errorMessage,
      });
    } finally {
      setIsInitializing(false);
    }
  };

  // Calculate taxes
  const calculate = async (params: CalcParams): Promise<CalcResult> => {
    if (!isReady) {
      throw new Error('CLI is not ready. Please initialize first.');
    }

    try {
      console.log('Calculating taxes with params:', params);
      const result: CalcResult = await invoke('calc', { params });
      console.log('Calculation completed:', result);
      return result;
    } catch (err) {
      const errorMessage = err as string;
      console.error('Tax calculation failed:', errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Get CLI status and auto-initialize on mount
  useEffect(() => {
    const getInitialStatusAndConnect = async () => {
      try {
        const statusInfo: CliStatusInfo = await invoke('get_cli_status');
        setStatus(statusInfo);
        
        // If not already initialized, try to auto-initialize
        if (!statusInfo.initialized) {
          console.log('CLI not initialized, attempting auto-connect...');
          try {
            setIsInitializing(true);
            setError(null);
            
            const versionInfo: VersionInfo = await invoke('init_cli');
            
            setStatus({
              initialized: true,
              version_info: versionInfo,
              error: null,
            });
            
            console.log('CLI auto-initialized successfully:', versionInfo);
          } catch (initErr) {
            const initErrorMessage = initErr as string;
            console.error('Auto-initialization failed:', initErrorMessage);
            
            setError(initErrorMessage);
            setStatus({
              initialized: false,
              version_info: null,
              error: initErrorMessage,
            });
          } finally {
            setIsInitializing(false);
          }
        } else if (statusInfo.error) {
          setError(statusInfo.error);
        }
      } catch (err) {
        const errorMessage = err as string;
        console.error('Failed to get CLI status:', errorMessage);
        setError(errorMessage);
      }
    };

    getInitialStatusAndConnect();
  }, []);

  const value: CliContextType = {
    status,
    isInitializing,
    error,
    initializeCli,
    calculate,
    isReady,
  };

  return (
    <CliContext.Provider value={value}>
      {children}
    </CliContext.Provider>
  );
};

// Hook to use CLI context
export const useCli = (): CliContextType => {
  const context = useContext(CliContext);
  if (context === undefined) {
    throw new Error('useCli must be used within a CliProvider');
  }
  return context;
};

export default CliContext;
