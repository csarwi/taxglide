import React from 'react';
import { createCardStyle, theme } from '../theme';

const Optimizer: React.FC = () => {
  return (
    <div style={createCardStyle()}>
      <h2 style={{
        marginTop: 0,
        marginBottom: theme.spacing.lg,
        color: theme.colors.primary,
        fontSize: theme.fontSizes.xl,
      }}>
        🎯 Tax Optimizer
      </h2>
      
      <div style={{
        textAlign: 'center',
        padding: theme.spacing.xl,
        color: theme.colors.textSecondary,
        fontSize: theme.fontSizes.md,
      }}>
        <p>Coming soon! This will help you find optimal deduction strategies.</p>
        <p style={{ marginTop: theme.spacing.md, fontSize: theme.fontSizes.sm }}>
          The optimizer will analyze different deduction amounts to maximize your tax savings.
        </p>
      </div>
    </div>
  );
};

export default Optimizer;
