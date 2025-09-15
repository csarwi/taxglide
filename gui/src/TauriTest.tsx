import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

function TauriTest() {
  const [result, setResult] = useState<string>("");
  const [loading, setLoading] = useState(false);

  const testGreet = async () => {
    try {
      setLoading(true);
      console.log("Testing basic Tauri command...");
      const response = await invoke("greet", { name: "TaxGlide" });
      console.log("Greet response:", response);
      setResult(`Greet: ${response}`);
    } catch (error) {
      console.error("Greet failed:", error);
      setResult(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const testIsCliReady = async () => {
    try {
      setLoading(true);
      console.log("Testing CLI ready check...");
      const response = await invoke("is_cli_ready");
      console.log("CLI Ready response:", response);
      setResult(`CLI Ready: ${response}`);
    } catch (error) {
      console.error("CLI Ready failed:", error);
      setResult(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const testInitCli = async () => {
    try {
      setLoading(true);
      console.log("Testing CLI initialization...");
      const response = await invoke("init_cli");
      console.log("Init CLI response:", response);
      setResult(`Init CLI: ${JSON.stringify(response, null, 2)}`);
    } catch (error) {
      console.error("Init CLI failed:", error);
      setResult(`Error: ${error}`);
    } finally {
      setLoading(false);
    }
  };

  const buttonStyle = {
    marginRight: "10px",
    padding: "8px 16px",
    backgroundColor: loading ? "#ccc" : "#007acc",
    color: "white",
    border: "none",
    borderRadius: "4px",
    cursor: loading ? "not-allowed" : "pointer",
    fontSize: "14px"
  };

  return (
    <div style={{ 
      padding: "20px", 
      fontFamily: "monospace", 
      border: "2px solid #007acc",
      borderRadius: "8px",
      backgroundColor: "#f8f9fa",
      color: "#333"
    }}>
      <h3 style={{ color: "#007acc", marginTop: 0 }}>🔧 Tauri Communication Test</h3>
      
      <div style={{ marginBottom: "15px" }}>
        <button onClick={testGreet} disabled={loading} style={buttonStyle}>
          {loading ? "⏳" : "✉️"} Test Greet
        </button>
        <button onClick={testIsCliReady} disabled={loading} style={buttonStyle}>
          {loading ? "⏳" : "❓"} Test CLI Ready
        </button>
        <button onClick={testInitCli} disabled={loading} style={buttonStyle}>
          {loading ? "⏳" : "🚀"} Test Init CLI
        </button>
      </div>

      {loading && (
        <div style={{ 
          color: "#007acc", 
          fontWeight: "bold",
          marginBottom: "10px",
          display: "flex",
          alignItems: "center"
        }}>
          <span style={{ marginRight: "8px" }}>⏳</span>
          Processing...
        </div>
      )}
      
      <div style={{ 
        marginTop: "10px", 
        padding: "15px", 
        backgroundColor: "#ffffff", 
        border: "2px solid #e9ecef",
        borderRadius: "6px",
        whiteSpace: "pre-wrap",
        minHeight: "120px",
        color: "#333",
        fontFamily: "'Courier New', monospace",
        fontSize: "13px"
      }}>
        <strong style={{ color: "#007acc" }}>📋 Result:</strong><br /><br />
        {result || <em style={{ color: "#6c757d" }}>(no result yet - click a button to test)</em>}
      </div>

      <div style={{ 
        marginTop: "10px", 
        fontSize: "12px", 
        color: "#6c757d",
        fontStyle: "italic"
      }}>
        💡 Tip: Check the browser console (F12) for detailed logs.
      </div>
    </div>
  );
}

export default TauriTest;
