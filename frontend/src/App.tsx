import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProcessPage from './pages/ProcessPage';
import AnalyticsPage from './pages/AnalyticsPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <nav className="nav">
          <div className="nav-container">
            <h1 className="nav-title">Tiered Email Filtering</h1>
            <div className="nav-links">
              <a href="/">Process</a>
              <a href="/history">History</a>
              <a href="/settings">Settings</a>
            </div>
          </div>
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<ProcessPage />} />
            <Route path="/analytics/:jobId" element={<AnalyticsPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;

