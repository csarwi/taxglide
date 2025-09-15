import React from 'react';
import { createCardStyle, theme } from '../theme';

const Scanner: React.FC = () => {
  return (
    <div style={createCardStyle()}>
      <h2 style={{
        marginTop: 0,
        marginBottom: theme.spacing.lg,
        color: theme.colors.primary,
        fontSize: theme.fontSizes.xl,
      }}>
        🔍 Deduction Scanner
      </h2>
      
      <div style={{
        textAlign: 'center',
        padding: theme.spacing.xl,
        color: theme.colors.textSecondary,
        fontSize: theme.fontSizes.md,
      }}>
        <p>Coming soon! This will scan ranges of deduction amounts.</p>
        <p style={{ marginTop: theme.spacing.md, fontSize: theme.fontSizes.sm }}>
          The scanner will help you visualize how different deduction levels affect your taxes.
        </p>
      </div>
    </div>
  );
};

export default Scanner;
