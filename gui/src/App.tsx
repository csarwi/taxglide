import { useState } from "react";
import reactLogo from "./assets/react.svg";
import { invoke } from "@tauri-apps/api/core";
import CliTester from "./CliTester";
import TauriTest from "./TauriTest";
import "./App.css";

function App() {
  const [greetMsg, setGreetMsg] = useState("");
  const [name, setName] = useState("");
  const [showCliTester, setShowCliTester] = useState(false);

  async function greet() {
    // Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
    setGreetMsg(await invoke("greet", { name }));
  }

  return (
    <main className="container">
      <h1>TaxGlide GUI</h1>

      <div className="row">
        <a href="https://vite.dev" target="_blank">
          <img src="/vite.svg" className="logo vite" alt="Vite logo" />
        </a>
        <a href="https://tauri.app" target="_blank">
          <img src="/tauri.svg" className="logo tauri" alt="Tauri logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      
      <div style={{ marginBottom: "20px" }}>
        <button 
          onClick={() => setShowCliTester(!showCliTester)}
          style={{ 
            padding: "10px 20px", 
            fontSize: "16px", 
            backgroundColor: showCliTester ? "#ffa500" : "#0070f3", 
            color: "white", 
            border: "none", 
            borderRadius: "5px",
            cursor: "pointer"
          }}
        >
          {showCliTester ? "Hide CLI Tester" : "Show CLI Tester"}
        </button>
      </div>

      {showCliTester ? (
        <>
          <TauriTest />
          <hr style={{ margin: "20px 0" }} />
          <CliTester />
        </>
      ) : (
        <>
          <p>Click on the Tauri, Vite, and React logos to learn more.</p>
          <form
            className="row"
            onSubmit={(e) => {
              e.preventDefault();
              greet();
            }}
          >
            <input
              id="greet-input"
              onChange={(e) => setName(e.currentTarget.value)}
              placeholder="Enter a name..."
            />
            <button type="submit">Greet</button>
          </form>
          <p>{greetMsg}</p>
        </>
      )}
    </main>
  );
}

export default App;
