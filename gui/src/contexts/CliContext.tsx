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
  canton?: string;
  municipality?: string;
}

// Updated CalcResult based on actual backend response
export interface CalcResult {
  income_sg: number;
  income_fed: number;
  income: number | null;
  federal: number;
  sg_simple: number;
  sg_after_mult: number;
  total: number;
  avg_rate: number;
  marginal_total: number;
  marginal_federal_hundreds: number;
  picks: string[];
  filing_status: string;
  feuer_warning?: string;
  canton_name?: string;
  canton_key?: string;
  municipality_name?: string;
  municipality_key?: string;
}

// Optimize command parameters
export interface OptimizeParams {
  year: number;
  income?: number;
  income_sg?: number;
  income_fed?: number;
  filing_status?: string;
  pick: string[];
  skip: string[];
  max_deduction?: number;
  tolerance_bp?: number;
  canton?: string;
  municipality?: string;
}

// Optimize command result based on contract documentation
export interface OptimizeResult {
  base_total: number;
  best_rate: {
    deduction: number;
    new_income: number;
    total: number;
    saved: number;
    savings_rate: number;
    savings_rate_percent: number;
  };
  plateau_near_max_roi: {
    min_d: number;
    max_d: number;
    roi_min_percent: number;
    roi_max_percent: number;
    tolerance_bp: number;
  };
  sweet_spot: {
    deduction: number;
    new_income: number;
    total_tax_at_spot: number;
    tax_saved_absolute: number;
    tax_saved_percent: number;
    federal_tax_at_spot: number;
    sg_tax_at_spot: number;
    baseline: {
      total_tax: number;
      federal_tax: number;
      sg_tax: number;
    };
    explanation: string;
    income_details: {
      original_sg: number;
      original_fed: number;
      after_deduction_sg: number;
      after_deduction_fed: number;
    };
    multipliers: {
      applied: string[];
      total_rate: number;
      feuer_warning?: string;
    };
    optimization_summary: {
      roi_percent: number;
      plateau_width_chf: number;
      federal_bracket_changed: boolean;
      marginal_rate_percent: number;
    };
  };
  federal_100_nudge: {
    nudge_chf: number;
    estimated_federal_saving: number;
  };
  adaptive_retry_used: {
    original_tolerance_bp: number;
    chosen_tolerance_bp: number;
    roi_improvement: number;
    utilization_improvement: number;
    selection_reason: string;
  };
  multipliers_applied: string[];
  tolerance_info: {
    tolerance_used_bp: number;
    tolerance_percent: number;
    tolerance_source: string;
    explanation: string;
  };
  canton_name?: string;
  canton_key?: string;
  municipality_name?: string;
  municipality_key?: string;
}

// Scan command parameters
export interface ScanParams {
  year: number;
  income?: number;
  income_sg?: number;
  income_fed?: number;
  max_deduction: number;
  d_step?: number;
  filing_status?: string;
  pick: string[];
  skip: string[];
  include_local_marginal?: boolean;
  canton?: string;
  municipality?: string;
}

// Scan result row based on CLI scan command output
export interface ScanResultRow {
  deduction: number;
  new_income: number;
  new_income_sg?: number;
  new_income_fed?: number;
  total_tax: number;
  saved: number;
  roi_percent: number;
  sg_simple: number;
  sg_after_multipliers: number;
  federal: number;
  federal_from: number;
  federal_to: number | null;
  federal_per100: number;
  local_marginal_percent: number | null;
}

export type ScanResult = ScanResultRow[];

// Canton and Municipality interfaces
export interface Municipality {
  name: string;
  key: string;
}

export interface Canton {
  name: string;
  key: string;
  municipalities: Municipality[];
}

export interface AvailableLocations {
  cantons: Canton[];
  defaults: {
    canton: string;
    municipality: string;
  };
}

// Context type
interface CliContextType {
  status: CliStatusInfo | null;
  isInitializing: boolean;
  error: string | null;
  initializeCli: () => Promise<void>;
  calculate: (params: CalcParams) => Promise<CalcResult>;
  optimize: (params: OptimizeParams) => Promise<OptimizeResult>;
  scan: (params: ScanParams) => Promise<ScanResult>;
  getAvailableLocations: () => Promise<AvailableLocations>;
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

  // Optimize tax strategy
  const optimize = async (params: OptimizeParams): Promise<OptimizeResult> => {
    if (!isReady) {
      throw new Error('CLI is not ready. Please initialize first.');
    }

    try {
      console.log('Optimizing tax strategy with params:', params);
      const result: OptimizeResult = await invoke('optimize', { params });
      console.log('Optimization completed:', result);
      return result;
    } catch (err) {
      const errorMessage = err as string;
      console.error('Tax optimization failed:', errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Scan deduction ranges
  const scan = async (params: ScanParams): Promise<ScanResult> => {
    if (!isReady) {
      throw new Error('CLI is not ready. Please initialize first.');
    }

    try {
      console.log('Scanning deduction ranges with params:', params);
      const result: ScanResult = await invoke('scan', { params });
      console.log('Scan completed:', result);
      return result;
    } catch (err) {
      const errorMessage = err as string;
      console.error('Scan failed:', errorMessage);
      throw new Error(errorMessage);
    }
  };

  // Get available cantons and municipalities
  const getAvailableLocations = async (): Promise<AvailableLocations> => {
    if (!isReady) {
      throw new Error('CLI is not ready. Please initialize first.');
    }

    try {
      console.log('Getting available cantons and municipalities...');
      const result: AvailableLocations = await invoke('get_available_locations');
      console.log('Available locations loaded:', result);
      return result;
    } catch (err) {
      const errorMessage = err as string;
      console.error('Failed to get available locations:', errorMessage);
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
    optimize,
    scan,
    getAvailableLocations,
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
