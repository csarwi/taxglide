import React from 'react';
import { createCardStyle, theme } from '../theme';

const Comparator: React.FC = () => {
  return (
    <div style={createCardStyle()}>
      <h2 style={{
        marginTop: 0,
        marginBottom: theme.spacing.lg,
        color: theme.colors.primary,
        fontSize: theme.fontSizes.xl,
      }}>
        ⚖️ Tax Comparator
      </h2>
      
      <div style={{
        textAlign: 'center',
        padding: theme.spacing.xl,
        color: theme.colors.textSecondary,
        fontSize: theme.fontSizes.md,
      }}>
        <p>Coming soon! This will help you compare different tax scenarios side-by-side.</p>
        <p style={{ marginTop: theme.spacing.md, fontSize: theme.fontSizes.sm }}>
          The comparator will let you analyze multiple tax scenarios to make informed decisions.
        </p>
      </div>
    </div>
  );
};

export default Comparator;
