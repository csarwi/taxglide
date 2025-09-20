import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { CliProvider } from './contexts/CliContext';
import { SharedFormProvider } from './contexts/SharedFormContext';
import AppShell from './components/AppShell';
import ErrorBoundary from './components/ErrorBoundary';
import Calculator from './views/Calculator';
import Optimizer from './views/Optimizer';
import Scanner from './views/Scanner';
import Settings from './views/Settings';
import Debug from './views/Debug';
import Info from './views/Info';

function App() {
  return (
    <ErrorBoundary>
      <SharedFormProvider>
        <CliProvider>
          <Router>
            <Routes>
              <Route path="/" element={<AppShell />}>
                <Route index element={<Calculator />} />
                <Route path="optimizer" element={<Optimizer />} />
                <Route path="scanner" element={<Scanner />} />
                <Route path="settings" element={<Settings />} />
                <Route path="info" element={<Info />} />
                <Route path="debug" element={<Debug />} />
              </Route>
            </Routes>
          </Router>
        </CliProvider>
      </SharedFormProvider>
    </ErrorBoundary>
  );
}

export default App;
