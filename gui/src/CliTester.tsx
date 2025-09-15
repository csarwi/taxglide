import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface VersionInfo {
  version: string;
  schema_version: string;
  build_timestamp: string;
  build_date: string;
  platform: string;
  supported_years: number[];
}

interface CliStatusInfo {
  initialized: boolean;
  version_info: VersionInfo | null;
  error: string | null;
}

interface CalcResult {
  year: number;
  total_income: number;
  total_tax: number;
  effective_rate: number;
  marginal_rate: number;
  taxes: {
    federal_income: number;
    singapore_income: number;
    us_social_security: number;
    us_medicare: number;
    singapore_cpf: number;
  };
  warnings: string[];
  multipliers_applied: string[];
}

function CliTester() {
  const [status, setStatus] = useState<CliStatusInfo | null>(null);
  const [calcResult, setCalcResult] = useState<CalcResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initializeCli = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log("Initializing CLI...");
      const versionInfo: VersionInfo = await invoke("init_cli");
      
      console.log("CLI initialized:", versionInfo);
      setStatus({
        initialized: true,
        version_info: versionInfo,
        error: null,
      });
    } catch (err) {
      console.error("Failed to initialize CLI:", err);
      setError(err as string);
      setStatus({
        initialized: false,
        version_info: null,
        error: err as string,
      });
    } finally {
      setLoading(false);
    }
  };

  const getCliStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log("Getting CLI status...");
      const statusInfo: CliStatusInfo = await invoke("get_cli_status");
      
      console.log("CLI status:", statusInfo);
      setStatus(statusInfo);
    } catch (err) {
      console.error("Failed to get CLI status:", err);
      setError(err as string);
    } finally {
      setLoading(false);
    }
  };

  const testCalc = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log("Running calc command...");
      const params = {
        year: 2025,
        income: 80000,
        filing_status: null,
        income_sg: null,
        income_fed: null,
        pick: [],
        skip: [],
      };
      
      console.log("Calc params:", params);
      const result: CalcResult = await invoke("calc", { params });
      
      console.log("Calc result:", result);
      setCalcResult(result);
    } catch (err) {
      console.error("Failed to run calc:", err);
      setError(err as string);
    } finally {
      setLoading(false);
    }
  };

  const buttonStyle = {
    padding: "10px 18px",
    marginRight: "12px",
    marginBottom: "8px",
    backgroundColor: loading ? "#6c757d" : "#28a745",
    color: "white",
    border: "none",
    borderRadius: "6px",
    cursor: loading ? "not-allowed" : "pointer",
    fontSize: "14px",
    fontWeight: "500",
    minWidth: "120px"
  };

  const disabledButtonStyle = {
    ...buttonStyle,
    backgroundColor: "#6c757d",
    cursor: "not-allowed"
  };

  return (
    <div style={{ 
      padding: "20px", 
      fontFamily: "system-ui, -apple-system, sans-serif",
      backgroundColor: "#ffffff",
      border: "2px solid #28a745",
      borderRadius: "10px",
      color: "#333"
    }}>
      <h2 style={{ color: "#28a745", marginTop: 0, marginBottom: "20px" }}>
        🧮 CLI Integration Tester
      </h2>
      
      <div style={{ marginBottom: "25px" }}>
        <button 
          onClick={initializeCli} 
          disabled={loading} 
          style={loading ? disabledButtonStyle : buttonStyle}
        >
          {loading ? "⏳ Working..." : "🚀 Initialize CLI"}
        </button>
        <button 
          onClick={getCliStatus} 
          disabled={loading} 
          style={loading ? disabledButtonStyle : buttonStyle}
        >
          {loading ? "⏳ Working..." : "📊 Get Status"}
        </button>
        <button 
          onClick={testCalc} 
          disabled={loading || !status?.initialized} 
          style={(loading || !status?.initialized) ? disabledButtonStyle : buttonStyle}
        >
          {loading ? "⏳ Working..." : "🧮 Test Calc"}
        </button>
      </div>

      {loading && (
        <div style={{ 
          color: "#007acc", 
          fontWeight: "bold",
          marginBottom: "15px",
          padding: "12px",
          backgroundColor: "#e3f2fd",
          border: "2px solid #007acc",
          borderRadius: "6px",
          display: "flex",
          alignItems: "center"
        }}>
          <span style={{ marginRight: "8px" }}>⏳</span>
          Processing request...
        </div>
      )}

      {error && (
        <div style={{ 
          color: "#721c24", 
          marginBottom: "15px", 
          backgroundColor: "#f8d7da", 
          padding: "15px", 
          border: "2px solid #dc3545",
          borderRadius: "6px"
        }}>
          <strong>❌ Error:</strong> {error}
        </div>
      )}

      {status && (
        <div style={{ 
          marginBottom: "25px", 
          backgroundColor: status.initialized ? "#d4edda" : "#f8d7da", 
          padding: "18px", 
          border: `2px solid ${status.initialized ? "#28a745" : "#dc3545"}`,
          borderRadius: "8px"
        }}>
          <h3 style={{ 
            color: status.initialized ? "#155724" : "#721c24", 
            marginTop: 0,
            marginBottom: "12px"
          }}>
            {status.initialized ? "✅" : "❌"} CLI Status
          </h3>
          <p style={{ margin: "8px 0", fontSize: "14px" }}>
            <strong>Status:</strong> 
            <span style={{ 
              color: status.initialized ? "#28a745" : "#dc3545",
              fontWeight: "bold",
              marginLeft: "8px"
            }}>
              {status.initialized ? "🟢 Ready" : "🔴 Not Ready"}
            </span>
          </p>
          {status.version_info && (
            <div style={{ fontSize: "13px", color: "#495057" }}>
              <p style={{ margin: "6px 0" }}><strong>Version:</strong> {status.version_info.version}</p>
              <p style={{ margin: "6px 0" }}><strong>Schema:</strong> {status.version_info.schema_version}</p>
              <p style={{ margin: "6px 0" }}><strong>Platform:</strong> {status.version_info.platform}</p>
              <p style={{ margin: "6px 0" }}><strong>Build:</strong> {new Date(status.version_info.build_date || status.version_info.build_timestamp).toLocaleString()}</p>
              <p style={{ margin: "6px 0" }}><strong>Supported Years:</strong> {status.version_info.supported_years.join(", ")}</p>
            </div>
          )}
          {status.error && (
            <p style={{ color: "#721c24", margin: "8px 0", fontWeight: "bold" }}>
              <strong>❌ Error:</strong> {status.error}
            </p>
          )}
        </div>
      )}

      {calcResult && (
        <div style={{ 
          backgroundColor: "#d1ecf1", 
          padding: "20px", 
          border: "2px solid #bee5eb",
          borderRadius: "8px",
          color: "#0c5460"
        }}>
          <h3 style={{ color: "#0c5460", marginTop: 0, marginBottom: "15px" }}>
            📊 Tax Calculation Results
          </h3>
          
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "15px", marginBottom: "20px" }}>
            <div>
              <p style={{ margin: "8px 0", fontSize: "14px" }}><strong>Year:</strong> {calcResult.year}</p>
              <p style={{ margin: "8px 0", fontSize: "14px" }}><strong>Total Income:</strong> ${calcResult.total_income.toLocaleString()}</p>
              <p style={{ margin: "8px 0", fontSize: "14px" }}><strong>Total Tax:</strong> ${calcResult.total_tax.toLocaleString()}</p>
            </div>
            <div>
              <p style={{ margin: "8px 0", fontSize: "14px" }}><strong>Effective Rate:</strong> {(calcResult.effective_rate * 100).toFixed(2)}%</p>
              <p style={{ margin: "8px 0", fontSize: "14px" }}><strong>Marginal Rate:</strong> {(calcResult.marginal_rate * 100).toFixed(2)}%</p>
            </div>
          </div>
          
          <h4 style={{ color: "#0c5460", marginBottom: "10px" }}>💰 Tax Breakdown</h4>
          <div style={{ 
            display: "grid", 
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", 
            gap: "8px",
            fontSize: "13px",
            marginBottom: "15px"
          }}>
            <div>• Federal Income: ${calcResult.taxes.federal_income.toLocaleString()}</div>
            <div>• Singapore Income: ${calcResult.taxes.singapore_income.toLocaleString()}</div>
            <div>• US Social Security: ${calcResult.taxes.us_social_security.toLocaleString()}</div>
            <div>• US Medicare: ${calcResult.taxes.us_medicare.toLocaleString()}</div>
            <div>• Singapore CPF: ${calcResult.taxes.singapore_cpf.toLocaleString()}</div>
          </div>
          
          {calcResult.warnings.length > 0 && (
            <div style={{ marginBottom: "15px" }}>
              <h4 style={{ color: "#856404", marginBottom: "8px" }}>⚠️ Warnings</h4>
              <div style={{ fontSize: "13px" }}>
                {calcResult.warnings.map((warning, i) => (
                  <div key={i} style={{ color: "#856404", margin: "4px 0" }}>• {warning}</div>
                ))}
              </div>
            </div>
          )}
          
          {calcResult.multipliers_applied.length > 0 && (
            <div>
              <h4 style={{ color: "#0c5460", marginBottom: "8px" }}>🔧 Multipliers Applied</h4>
              <div style={{ fontSize: "13px" }}>
                {calcResult.multipliers_applied.map((multiplier, i) => (
                  <div key={i} style={{ margin: "4px 0" }}>• {multiplier}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CliTester;
