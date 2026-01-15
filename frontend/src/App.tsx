import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import ProcessPage from './pages/ProcessPage';
import AnalyticsPage from './pages/AnalyticsPage';
import HistoryPage from './pages/HistoryPage';
import SettingsPage from './pages/SettingsPage';
import Sidebar from './components/Sidebar';
import { Button } from '@/components/ui/button';
import { Menu } from 'lucide-react';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="min-h-screen flex bg-background">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        <div className="flex-1 flex flex-col min-w-0 w-full lg:ml-64 transition-[margin] duration-300">
          <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b px-4 lg:px-8 flex items-center min-h-16">
            <Button
              variant="outline"
              size="icon"
              className="lg:hidden"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle menu"
              aria-expanded={sidebarOpen}
            >
              <Menu className="h-5 w-5" />
            </Button>
          </header>

          <main className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
            <div className="flex-1 flex flex-col w-full max-w-7xl mx-auto p-4 lg:p-8">
              <Routes>
                <Route path="/" element={<ProcessPage />} />
                <Route path="/analytics/:jobId" element={<AnalyticsPage />} />
                <Route path="/history" element={<HistoryPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </div>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
