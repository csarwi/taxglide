import React from 'react';
import { useCli } from '../contexts/CliContext';
import { theme } from '../theme';

interface StatusIndicatorProps {
  showDetails?: boolean;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ showDetails = false }) => {
  const { status, isInitializing, error, isReady, initializeCli } = useCli();

  const getStatusStyle = () => {
    if (isInitializing) {
      return {
        backgroundColor: theme.colors.statusWarning,
        borderColor: theme.colors.statusWarningBorder,
        color: theme.colors.text,
      };
    }
    
    if (isReady) {
      return {
        backgroundColor: theme.colors.statusSuccess,
        borderColor: theme.colors.statusSuccessBorder,
        color: theme.colors.text,
      };
    }
    
    return {
      backgroundColor: theme.colors.statusError,
      borderColor: theme.colors.statusErrorBorder,
      color: theme.colors.text,
    };
  };

  const getStatusText = () => {
    if (isInitializing) return 'Connecting...';
    if (isReady) return 'Connected';
    return 'Disconnected';
  };

  const getStatusIcon = () => {
    if (isInitializing) return '🔄';
    if (isReady) return '🟢';
    return '🔴';
  };

  const statusStyle = getStatusStyle();

  return (
    <div style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: showDetails ? theme.spacing.md : theme.spacing.sm,
      borderRadius: theme.borderRadius.md,
      border: '1px solid',
      fontSize: theme.fontSizes.sm,
      fontFamily: theme.fonts.body,
      ...statusStyle,
    }}>
      <span style={{ marginRight: theme.spacing.sm }}>
        {getStatusIcon()}
      </span>
      
      <span style={{ fontWeight: '500' }}>
        {getStatusText()}
      </span>

      {showDetails && status?.version_info && (
        <span style={{ 
          marginLeft: theme.spacing.sm,
          fontSize: theme.fontSizes.xs,
          opacity: 0.8,
        }}>
          v{status.version_info.version}
        </span>
      )}

      {!isReady && !isInitializing && (
        <button
          onClick={initializeCli}
          style={{
            marginLeft: theme.spacing.sm,
            padding: `${theme.spacing.xs} ${theme.spacing.sm}`,
            backgroundColor: theme.colors.primary,
            color: 'white',
            border: 'none',
            borderRadius: theme.borderRadius.sm,
            fontSize: theme.fontSizes.xs,
            cursor: 'pointer',
            fontFamily: theme.fonts.body,
          }}
        >
          Connect
        </button>
      )}

      {error && showDetails && (
        <div style={{
          marginTop: theme.spacing.sm,
          fontSize: theme.fontSizes.xs,
          color: theme.colors.error,
          maxWidth: '300px',
          wordBreak: 'break-word',
        }}>
          {error}
        </div>
      )}
    </div>
  );
};

export default StatusIndicator;
