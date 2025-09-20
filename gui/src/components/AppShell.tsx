import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import StatusIndicator from './StatusIndicator';
import { theme } from '../theme';

const AppShell: React.FC = () => {
  const navItems = [
    { path: '/', label: '🧮 Calculator', end: true },
    { path: '/optimizer', label: '🎯 Optimizer' },
    { path: '/scanner', label: '🔍 Scanner' },
    { path: '/settings', label: '⚙️ Settings' },
    { path: '/info', label: '📋 Info' },
    { path: '/debug', label: '🔧 Debug' },
  ];

  const navLinkStyle = {
    display: 'inline-block',
    padding: `${theme.spacing.sm} ${theme.spacing.md}`,
    marginRight: theme.spacing.sm,
    textDecoration: 'none',
    borderRadius: theme.borderRadius.md,
    fontSize: theme.fontSizes.sm,
    fontWeight: '500',
    transition: 'all 0.2s ease',
    fontFamily: theme.fonts.body,
  };

  const activeNavLinkStyle = {
    ...navLinkStyle,
    backgroundColor: theme.colors.primary,
    color: 'white',
  };

  const inactiveNavLinkStyle = {
    ...navLinkStyle,
    backgroundColor: 'transparent',
    color: theme.colors.textSecondary,
    border: `1px solid ${theme.colors.gray300}`,
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: theme.colors.backgroundSecondary,
      fontFamily: theme.fonts.body,
    }}>
      {/* Header */}
      <header style={{
        backgroundColor: theme.colors.background,
        borderBottom: `1px solid ${theme.colors.gray200}`,
        padding: `${theme.spacing.md} ${theme.spacing.xl}`,
        boxShadow: theme.shadows.sm,
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          maxWidth: '1200px',
          margin: '0 auto',
        }}>
          <h1 style={{
            margin: 0,
            fontSize: theme.fontSizes['2xl'],
            fontWeight: '700',
            color: theme.colors.primary,
            fontFamily: theme.fonts.heading,
          }}>
            TaxGlide
          </h1>
          
          <StatusIndicator showDetails={true} />
        </div>
      </header>

      {/* Navigation */}
      <nav style={{
        backgroundColor: theme.colors.background,
        borderBottom: `1px solid ${theme.colors.gray200}`,
        padding: `${theme.spacing.md} ${theme.spacing.xl}`,
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
        }}>
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              style={({ isActive }) => 
                isActive ? activeNavLinkStyle : inactiveNavLinkStyle
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Main Content */}
      <main style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: theme.spacing.xl,
        minHeight: 'calc(100vh - 140px)', // Adjust based on header/nav height
      }}>
        <Outlet />
      </main>

      {/* Footer */}
      <footer style={{
        backgroundColor: theme.colors.background,
        borderTop: `1px solid ${theme.colors.gray200}`,
        padding: `${theme.spacing.md} ${theme.spacing.xl}`,
        textAlign: 'center',
        color: theme.colors.textSecondary,
        fontSize: theme.fontSizes.sm,
      }}>
        <div style={{
          maxWidth: '1200px',
          margin: '0 auto',
        }}>
          TaxGlide - Advanced Tax Calculation & Optimization
        </div>
      </footer>
    </div>
  );
};

export default AppShell;
