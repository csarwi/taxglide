import React, { useState } from 'react';
import { theme } from '../theme';

interface InfoTooltipProps {
  children: React.ReactNode;
  content: React.ReactNode;
  title?: string;
}

const InfoTooltip: React.FC<InfoTooltipProps> = ({ children, content, title }) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        style={{
          cursor: 'help',
          color: theme.colors.primary,
          display: 'inline-flex',
          alignItems: 'center',
        }}
      >
        {children}
      </div>
      
      {isVisible && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginTop: theme.spacing.xs,
            background: theme.colors.background,
            border: `1px solid ${theme.colors.gray300}`,
            borderRadius: theme.borderRadius.md,
            padding: theme.spacing.md,
            minWidth: '300px',
            maxWidth: '400px',
            zIndex: 1000,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            fontSize: theme.fontSizes.sm,
            lineHeight: '1.5',
          }}
        >
          {title && (
            <div
              style={{
                fontWeight: '600',
                marginBottom: theme.spacing.sm,
                color: theme.colors.text,
                fontSize: theme.fontSizes.sm,
              }}
            >
              {title}
            </div>
          )}
          <div style={{ color: theme.colors.textSecondary }}>
            {content}
          </div>
          {/* Tooltip arrow */}
          <div
            style={{
              position: 'absolute',
              top: '-8px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: '0',
              height: '0',
              borderLeft: '8px solid transparent',
              borderRight: '8px solid transparent',
              borderBottom: `8px solid ${theme.colors.gray300}`,
            }}
          />
          <div
            style={{
              position: 'absolute',
              top: '-7px',
              left: '50%',
              transform: 'translateX(-50%)',
              width: '0',
              height: '0',
              borderLeft: '8px solid transparent',
              borderRight: '8px solid transparent',
              borderBottom: `8px solid ${theme.colors.background}`,
            }}
          />
        </div>
      )}
    </div>
  );
};

export default InfoTooltip;
