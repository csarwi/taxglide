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

  return (
    <div style={{ padding: "20px", fontFamily: "monospace", border: "2px solid #ccc" }}>
      <h3>Tauri Communication Test</h3>
      
      <div style={{ marginBottom: "10px" }}>
        <button onClick={testGreet} disabled={loading} style={{ marginRight: "10px" }}>
          Test Greet
        </button>
        <button onClick={testIsCliReady} disabled={loading} style={{ marginRight: "10px" }}>
          Test CLI Ready
        </button>
        <button onClick={testInitCli} disabled={loading}>
          Test Init CLI
        </button>
      </div>

      {loading && <div style={{ color: "blue" }}>Loading...</div>}
      
      <div style={{ 
        marginTop: "10px", 
        padding: "10px", 
        backgroundColor: "#f5f5f5", 
        border: "1px solid #ddd",
        whiteSpace: "pre-wrap",
        minHeight: "100px"
      }}>
        <strong>Result:</strong><br />
        {result || "(no result yet)"}
      </div>

      <div style={{ marginTop: "10px", fontSize: "12px", color: "#666" }}>
        Check the browser console (F12) for detailed logs.
      </div>
    </div>
  );
}

export default TauriTest;
