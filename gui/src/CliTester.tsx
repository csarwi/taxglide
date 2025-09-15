import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

interface VersionInfo {
  version: string;
  schema_version: string;
  build_timestamp: string;
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

  return (
    <div style={{ padding: "20px", fontFamily: "monospace" }}>
      <h2>CLI Integration Tester</h2>
      
      <div style={{ marginBottom: "20px" }}>
        <button onClick={initializeCli} disabled={loading}>
          Initialize CLI
        </button>
        <button onClick={getCliStatus} disabled={loading} style={{ marginLeft: "10px" }}>
          Get Status
        </button>
        <button 
          onClick={testCalc} 
          disabled={loading || !status?.initialized} 
          style={{ marginLeft: "10px" }}
        >
          Test Calc
        </button>
      </div>

      {loading && (
        <div style={{ color: "blue", marginBottom: "10px" }}>
          Loading...
        </div>
      )}

      {error && (
        <div style={{ color: "red", marginBottom: "10px", backgroundColor: "#fee", padding: "10px", border: "1px solid #fcc" }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {status && (
        <div style={{ marginBottom: "20px", backgroundColor: "#f0f0f0", padding: "10px", border: "1px solid #ccc" }}>
          <h3>CLI Status</h3>
          <p><strong>Initialized:</strong> {status.initialized ? "Yes" : "No"}</p>
          {status.version_info && (
            <div>
              <p><strong>Version:</strong> {status.version_info.version}</p>
              <p><strong>Schema Version:</strong> {status.version_info.schema_version}</p>
              <p><strong>Build Time:</strong> {status.version_info.build_timestamp}</p>
              <p><strong>Supported Years:</strong> {status.version_info.supported_years.join(", ")}</p>
            </div>
          )}
          {status.error && (
            <p style={{ color: "red" }}><strong>Error:</strong> {status.error}</p>
          )}
        </div>
      )}

      {calcResult && (
        <div style={{ backgroundColor: "#e8f5e8", padding: "10px", border: "1px solid #4c8a3b" }}>
          <h3>Calc Result</h3>
          <p><strong>Year:</strong> {calcResult.year}</p>
          <p><strong>Total Income:</strong> ${calcResult.total_income.toLocaleString()}</p>
          <p><strong>Total Tax:</strong> ${calcResult.total_tax.toLocaleString()}</p>
          <p><strong>Effective Rate:</strong> {(calcResult.effective_rate * 100).toFixed(2)}%</p>
          <p><strong>Marginal Rate:</strong> {(calcResult.marginal_rate * 100).toFixed(2)}%</p>
          
          <h4>Tax Breakdown</h4>
          <ul>
            <li>Federal Income: ${calcResult.taxes.federal_income.toLocaleString()}</li>
            <li>Singapore Income: ${calcResult.taxes.singapore_income.toLocaleString()}</li>
            <li>US Social Security: ${calcResult.taxes.us_social_security.toLocaleString()}</li>
            <li>US Medicare: ${calcResult.taxes.us_medicare.toLocaleString()}</li>
            <li>Singapore CPF: ${calcResult.taxes.singapore_cpf.toLocaleString()}</li>
          </ul>
          
          {calcResult.warnings.length > 0 && (
            <>
              <h4>Warnings</h4>
              <ul>
                {calcResult.warnings.map((warning, i) => (
                  <li key={i} style={{ color: "orange" }}>{warning}</li>
                ))}
              </ul>
            </>
          )}
          
          {calcResult.multipliers_applied.length > 0 && (
            <>
              <h4>Multipliers Applied</h4>
              <ul>
                {calcResult.multipliers_applied.map((multiplier, i) => (
                  <li key={i}>{multiplier}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default CliTester;
