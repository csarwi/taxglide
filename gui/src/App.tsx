import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CliProvider } from './contexts/CliContext';
import AppShell from './components/AppShell';
import ErrorBoundary from './components/ErrorBoundary';
import Calculator from './views/Calculator';
import Optimizer from './views/Optimizer';
import Scanner from './views/Scanner';
import Comparator from './views/Comparator';
import Debug from './views/Debug';

function App() {
  return (
    <ErrorBoundary>
      <CliProvider>
        <Router>
          <Routes>
            <Route path="/" element={<AppShell />}>
              <Route index element={<Calculator />} />
              <Route path="optimizer" element={<Optimizer />} />
              <Route path="scanner" element={<Scanner />} />
              <Route path="comparator" element={<Comparator />} />
              <Route path="debug" element={<Debug />} />
            </Route>
          </Routes>
        </Router>
      </CliProvider>
    </ErrorBoundary>
  );
}

export default App;
