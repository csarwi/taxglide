import React, { useState } from 'react';
import { theme } from '../theme';
import YearManager from '../components/YearManager';
import CantonManager from '../components/CantonManager';
import FederalBracketsManager from '../components/FederalBracketsManager';
import MunicipalityManager from '../components/MunicipalityManager';

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState('years');

  const tabs = [
    { id: 'years', label: '📅 Tax Years', component: YearManager },
    { id: 'federal', label: '🏛️ Federal Brackets', component: FederalBracketsManager },
    { id: 'cantons', label: '🏔️ Cantons', component: CantonManager },
    { id: 'municipalities', label: '🏙️ Municipalities', component: MunicipalityManager },
  ];

  const tabStyle = (isActive: boolean) => ({
    padding: `${theme.spacing.md} ${theme.spacing.lg}`,
    border: 'none',
    backgroundColor: isActive ? theme.colors.primary : 'transparent',
    color: isActive ? 'white' : theme.colors.textSecondary,
    cursor: 'pointer',
    borderRadius: `${theme.borderRadius.md} ${theme.borderRadius.md} 0 0`,
    fontSize: theme.fontSizes.sm,
    fontWeight: '500',
    transition: 'all 0.2s ease',
    marginRight: theme.spacing.xs,
  });

  const ActiveComponent = tabs.find(tab => tab.id === activeTab)?.component || YearManager;

  return (
    <div style={{
      maxWidth: '1200px',
      margin: '0 auto',
      padding: theme.spacing.lg,
    }}>
      {/* Header */}
      <div style={{ marginBottom: theme.spacing.xl }}>
        <h1 style={{
          fontSize: theme.fontSizes['3xl'],
          fontWeight: '700',
          color: theme.colors.primary,
          margin: 0,
          marginBottom: theme.spacing.sm,
        }}>
          ⚙️ Configuration Settings
        </h1>
        <p style={{
          color: theme.colors.textSecondary,
          fontSize: theme.fontSizes.md,
          margin: 0,
        }}>
          Manage tax years, federal brackets, cantons, and municipalities
        </p>
      </div>

      {/* Tab Navigation */}
      <div style={{
        borderBottom: `2px solid ${theme.colors.gray200}`,
        marginBottom: theme.spacing.xl,
      }}>
        <div style={{ display: 'flex' }}>
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={tabStyle(activeTab === tab.id)}
              onMouseEnter={(e) => {
                if (activeTab !== tab.id) {
                  e.currentTarget.style.backgroundColor = theme.colors.gray100;
                }
              }}
              onMouseLeave={(e) => {
                if (activeTab !== tab.id) {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Active Tab Content */}
      <div style={{
        backgroundColor: theme.colors.background,
        borderRadius: theme.borderRadius.lg,
        padding: theme.spacing.xl,
        boxShadow: theme.shadows.md,
        border: `1px solid ${theme.colors.gray200}`,
        minHeight: '600px',
      }}>
        <ActiveComponent />
      </div>
    </div>
  );
};

export default Settings;