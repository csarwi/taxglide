import React, { Component, ReactNode } from 'react';
import { theme, createCardStyle } from '../theme';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={createCardStyle()}>
          <h2 style={{
            color: theme.colors.error,
            marginTop: 0,
            marginBottom: theme.spacing.lg,
          }}>
            ❌ Something went wrong
          </h2>
          
          <div style={{
            backgroundColor: theme.colors.statusError,
            border: `1px solid ${theme.colors.statusErrorBorder}`,
            borderRadius: theme.borderRadius.md,
            padding: theme.spacing.md,
            marginBottom: theme.spacing.lg,
          }}>
            <p style={{ margin: 0, fontWeight: '500' }}>
              The application encountered an unexpected error.
            </p>
          </div>

          {this.state.error && (
            <details style={{
              backgroundColor: theme.colors.backgroundSecondary,
              border: `1px solid ${theme.colors.gray300}`,
              borderRadius: theme.borderRadius.md,
              padding: theme.spacing.md,
              fontSize: theme.fontSizes.sm,
              fontFamily: theme.fonts.mono,
            }}>
              <summary style={{ cursor: 'pointer', fontWeight: '500' }}>
                Error Details
              </summary>
              <pre style={{
                marginTop: theme.spacing.md,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {this.state.error.toString()}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}

          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: theme.spacing.lg,
              padding: `${theme.spacing.sm} ${theme.spacing.md}`,
              backgroundColor: theme.colors.primary,
              color: 'white',
              border: 'none',
              borderRadius: theme.borderRadius.md,
              fontSize: theme.fontSizes.sm,
              cursor: 'pointer',
              fontFamily: theme.fonts.body,
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
