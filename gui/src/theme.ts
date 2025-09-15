// Design System Theme
export const theme = {
  colors: {
    primary: '#007acc',
    primaryHover: '#005a99',
    success: '#28a745',
    successHover: '#218838',
    warning: '#ffc107',
    warningHover: '#e0a800',
    error: '#dc3545',
    errorHover: '#c82333',
    
    // Grays
    gray50: '#f8f9fa',
    gray100: '#e9ecef',
    gray200: '#dee2e6',
    gray300: '#ced4da',
    gray400: '#adb5bd',
    gray500: '#6c757d',
    gray600: '#495057',
    gray700: '#343a40',
    gray800: '#212529',
    gray900: '#000000',
    
    // Backgrounds
    background: '#ffffff',
    backgroundSecondary: '#f8f9fa',
    backgroundTertiary: '#e9ecef',
    
    // Text
    text: '#212529',
    textSecondary: '#6c757d',
    textMuted: '#868e96',
    
    // Results colors
    resultsBackground: '#d1ecf1',
    resultsBorder: '#bee5eb',
    resultsText: '#0c5460',
    
    // Status colors
    statusSuccess: '#d4edda',
    statusSuccessBorder: '#c3e6cb',
    statusError: '#f8d7da',
    statusErrorBorder: '#f5c6cb',
    statusWarning: '#fff3cd',
    statusWarningBorder: '#ffeaa7',
  },
  
  fonts: {
    body: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
    mono: '"Courier New", Consolas, Monaco, monospace',
    heading: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  },
  
  fontSizes: {
    xs: '12px',
    sm: '14px',
    md: '16px',
    lg: '18px',
    xl: '20px',
    '2xl': '24px',
    '3xl': '30px',
    '4xl': '36px',
  },
  
  spacing: {
    xs: '4px',
    sm: '8px',
    md: '16px',
    lg: '24px',
    xl: '32px',
    '2xl': '48px',
    '3xl': '64px',
  },
  
  borderRadius: {
    sm: '4px',
    md: '6px',
    lg: '8px',
    xl: '12px',
    full: '50%',
  },
  
  shadows: {
    sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px rgba(0, 0, 0, 0.15)',
  },
  
  breakpoints: {
    sm: '640px',
    md: '768px',
    lg: '1024px',
    xl: '1280px',
  },
};

// Common style helpers
export const createButtonStyle = (variant: 'primary' | 'secondary' | 'success' | 'warning' | 'error' = 'primary', disabled = false) => ({
  padding: `${theme.spacing.sm} ${theme.spacing.md}`,
  fontSize: theme.fontSizes.sm,
  fontWeight: '500',
  borderRadius: theme.borderRadius.md,
  border: 'none',
  cursor: disabled ? 'not-allowed' : 'pointer',
  transition: 'all 0.2s ease',
  fontFamily: theme.fonts.body,
  
  ...(disabled ? {
    backgroundColor: theme.colors.gray400,
    color: 'white',
  } : {
    backgroundColor: theme.colors[variant],
    color: 'white',
    ':hover': {
      backgroundColor: theme.colors[`${variant}Hover` as keyof typeof theme.colors],
    }
  }),
});

export const createCardStyle = () => ({
  backgroundColor: theme.colors.background,
  border: `2px solid ${theme.colors.gray200}`,
  borderRadius: theme.borderRadius.lg,
  padding: theme.spacing.lg,
  boxShadow: theme.shadows.sm,
});

export const createInputStyle = () => ({
  width: '100%',
  boxSizing: 'border-box' as const,
  padding: `${theme.spacing.sm} ${theme.spacing.md}`,
  fontSize: theme.fontSizes.sm,
  border: `1px solid ${theme.colors.gray300}`,
  borderRadius: theme.borderRadius.md,
  fontFamily: theme.fonts.body,
  transition: 'border-color 0.2s ease',
  
  ':focus': {
    outline: 'none',
    borderColor: theme.colors.primary,
    boxShadow: `0 0 0 2px ${theme.colors.primary}20`,
  },
});

export type Theme = typeof theme;
