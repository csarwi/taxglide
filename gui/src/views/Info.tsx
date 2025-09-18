import React from 'react';
import { theme, createCardStyle } from '../theme';

const Info: React.FC = () => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: theme.spacing.xl,
      maxWidth: '800px',
      margin: '0 auto',
    }}>
      {/* Header */}
      <div style={createCardStyle()}>
        <h1 style={{
          marginTop: 0,
          marginBottom: theme.spacing.lg,
          color: theme.colors.primary,
          fontSize: theme.fontSizes['2xl'],
          textAlign: 'center',
        }}>
          🚧 TaxGlide - Beta Information
        </h1>
        
        <div style={{
          backgroundColor: theme.colors.statusWarning,
          border: `1px solid ${theme.colors.statusWarningBorder}`,
          borderRadius: theme.borderRadius.md,
          padding: theme.spacing.lg,
          marginBottom: theme.spacing.lg,
          textAlign: 'center',
        }}>
          <h3 style={{
            margin: `0 0 ${theme.spacing.md} 0`,
            color: theme.colors.text,
            fontSize: theme.fontSizes.lg,
          }}>
            ⚠️ Beta Software Notice
          </h3>
          <p style={{
            margin: 0,
            color: theme.colors.text,
            fontSize: theme.fontSizes.md,
            lineHeight: '1.6',
          }}>
            TaxGlide is currently in <strong>beta</strong> and is primarily intended for <strong>personal use</strong>. 
            While we strive for accuracy, please verify all calculations with official tax authorities or professional advisors.
          </p>
        </div>

        <div style={{
          fontSize: theme.fontSizes.md,
          lineHeight: '1.7',
          color: theme.colors.text,
        }}>
          <p>
            Welcome to TaxGlide! This Swiss tax calculation tool is designed to help you understand 
            your federal and cantonal tax obligations. We support multiple Swiss cantons and 
            municipalities, with ongoing work to expand coverage across all of Switzerland.
          </p>
          
          <p>
            The tool provides tax calculations, optimization suggestions, and detailed analysis 
            to help you make informed financial decisions. All calculations are based on official 
            Swiss tax regulations and rates.
          </p>
        </div>
      </div>

      {/* Current Features */}
      <div style={createCardStyle()}>
        <h2 style={{
          marginTop: 0,
          marginBottom: theme.spacing.lg,
          color: theme.colors.primary,
          fontSize: theme.fontSizes.xl,
        }}>
          ✅ Current Features
        </h2>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: theme.spacing.lg,
        }}>
          <div>
            <h4 style={{
              margin: `0 0 ${theme.spacing.sm} 0`,
              color: theme.colors.text,
              fontSize: theme.fontSizes.md,
            }}>
              🧮 Tax Calculator
            </h4>
            <ul style={{
              margin: 0,
              paddingLeft: theme.spacing.lg,
              color: theme.colors.textSecondary,
              fontSize: theme.fontSizes.sm,
            }}>
              <li>Federal and cantonal tax calculations</li>
              <li>Single and married filing status support</li>
              <li>Separate income handling</li>
              <li>Real-time location selection</li>
            </ul>
          </div>
          
          <div>
            <h4 style={{
              margin: `0 0 ${theme.spacing.sm} 0`,
              color: theme.colors.text,
              fontSize: theme.fontSizes.md,
            }}>
              🎯 Tax Optimizer
            </h4>
            <ul style={{
              margin: 0,
              paddingLeft: theme.spacing.lg,
              color: theme.colors.textSecondary,
              fontSize: theme.fontSizes.sm,
            }}>
              <li>Deduction optimization strategies</li>
              <li>ROI analysis and plateau detection</li>
              <li>Adaptive optimization algorithms</li>
              <li>Tax bracket transition analysis</li>
            </ul>
          </div>
          
          <div>
            <h4 style={{
              margin: `0 0 ${theme.spacing.sm} 0`,
              color: theme.colors.text,
              fontSize: theme.fontSizes.md,
            }}>
              🔍 Deduction Scanner
            </h4>
            <ul style={{
              margin: 0,
              paddingLeft: theme.spacing.lg,
              color: theme.colors.textSecondary,
              fontSize: theme.fontSizes.sm,
            }}>
              <li>Comprehensive deduction analysis</li>
              <li>Interactive data tables</li>
              <li>Marginal tax rate calculations</li>
              <li>Data filtering capabilities</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Future Roadmap */}
      <div style={createCardStyle()}>
        <h2 style={{
          marginTop: 0,
          marginBottom: theme.spacing.lg,
          color: theme.colors.primary,
          fontSize: theme.fontSizes.xl,
        }}>
          🚀 Coming Soon
        </h2>
        
        <div style={{
          fontSize: theme.fontSizes.md,
          lineHeight: '1.6',
          color: theme.colors.text,
        }}>
          <p style={{ marginBottom: theme.spacing.lg }}>
            We're continuously improving TaxGlide with exciting new features:
          </p>
          
          <div style={{
            display: 'grid',
            gap: theme.spacing.md,
          }}>
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: theme.spacing.md,
            }}>
              <span style={{ fontSize: theme.fontSizes.lg, minWidth: '24px' }}>🇩🇪</span>
              <div>
                <strong>German Language Support</strong>
                <br />
                <span style={{ color: theme.colors.textSecondary, fontSize: theme.fontSizes.sm }}>
                  Complete German translation for native Swiss German speakers
                </span>
              </div>
            </div>
            
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: theme.spacing.md,
            }}>
              <span style={{ fontSize: theme.fontSizes.lg, minWidth: '24px' }}>⛪</span>
              <div>
                <strong>Enhanced Church Tax Support</strong>
                <br />
                <span style={{ color: theme.colors.textSecondary, fontSize: theme.fontSizes.sm }}>
                  Better handling of religious tax obligations across different cantons
                </span>
              </div>
            </div>
            
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: theme.spacing.md,
            }}>
              <span style={{ fontSize: theme.fontSizes.lg, minWidth: '24px' }}>⚙️</span>
              <div>
                <strong>GUI Configuration Management</strong>
                <br />
                <span style={{ color: theme.colors.textSecondary, fontSize: theme.fontSizes.sm }}>
                  Easy-to-use interface for customizing tax rates and multipliers
                </span>
              </div>
            </div>
            
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: theme.spacing.md,
            }}>
              <span style={{ fontSize: theme.fontSizes.lg, minWidth: '24px' }}>🌍</span>
              <div>
                <strong>Community-Driven Configuration</strong>
                <br />
                <span style={{ color: theme.colors.textSecondary, fontSize: theme.fontSizes.sm }}>
                  Submit and share tax configurations for different cantons and municipalities
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Contact Information */}
      <div style={createCardStyle()}>
        <h2 style={{
          marginTop: 0,
          marginBottom: theme.spacing.lg,
          color: theme.colors.primary,
          fontSize: theme.fontSizes.xl,
        }}>
          💬 Get in Touch
        </h2>
        
        <div style={{
          backgroundColor: theme.colors.backgroundSecondary,
          border: `1px solid ${theme.colors.gray300}`,
          borderRadius: theme.borderRadius.md,
          padding: theme.spacing.lg,
          textAlign: 'center',
        }}>
          <h3 style={{
            margin: `0 0 ${theme.spacing.md} 0`,
            color: theme.colors.text,
            fontSize: theme.fontSizes.lg,
          }}>
            📧 Questions, Suggestions, or Feedback?
          </h3>
          
          <p style={{
            margin: `0 0 ${theme.spacing.md} 0`,
            color: theme.colors.textSecondary,
            fontSize: theme.fontSizes.md,
          }}>
            We'd love to hear from you! Whether you have questions about calculations, 
            suggestions for new features, or feedback about your experience:
          </p>
          
          <div style={{
            backgroundColor: theme.colors.backgroundTertiary,
            border: `1px solid ${theme.colors.gray200}`,
            borderRadius: theme.borderRadius.sm,
            padding: theme.spacing.md,
            display: 'inline-block',
            marginBottom: theme.spacing.md,
          }}>
            <a 
              href="mailto:chtonios@protonmail.com?subject=TaxGlide%20Feedback"
              style={{
                color: theme.colors.primary,
                textDecoration: 'none',
                fontWeight: '600',
                fontSize: theme.fontSizes.md,
              }}
            >
              📮 chtonios@protonmail.com
            </a>
          </div>
          
          <p style={{
            margin: 0,
            color: theme.colors.textSecondary,
            fontSize: theme.fontSizes.sm,
          }}>
            Your input helps us make TaxGlide better for everyone!
          </p>
        </div>
      </div>

      {/* Disclaimer */}
      <div style={{
        ...createCardStyle(),
        backgroundColor: theme.colors.backgroundSecondary,
        border: `1px solid ${theme.colors.gray300}`,
      }}>
        <h3 style={{
          marginTop: 0,
          marginBottom: theme.spacing.md,
          color: theme.colors.text,
          fontSize: theme.fontSizes.md,
        }}>
          ⚖️ Legal Disclaimer
        </h3>
        
        <p style={{
          margin: 0,
          color: theme.colors.textSecondary,
          fontSize: theme.fontSizes.sm,
          lineHeight: '1.5',
        }}>
          TaxGlide is provided for informational purposes only. While we strive for accuracy, 
          tax calculations should always be verified with official sources or professional tax advisors. 
          We are not liable for any decisions made based on calculations from this tool. 
          Always consult with qualified professionals for official tax advice.
        </p>
      </div>
    </div>
  );
};

export default Info;