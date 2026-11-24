import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { NewScanPage } from './pages/NewScanPage';
import { ScanProcessingPage } from './pages/ScanProcessingPage';
import { ScanDetailPage } from './pages/ScanDetailPage';
import { HistoryPage } from './pages/HistoryPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';
import { ReportsPage } from './pages/ReportsPage';
import { RulesPage } from './pages/RulesPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { SettingsPage } from './pages/SettingsPage';
import { ErrorBoundary } from './components/common/ErrorBoundary';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#f8f9ff] flex items-center justify-center text-xs text-gray-500">
        Verifying officer authorization...
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />

          <Route
            path="/"
            element={
              <ProtectedRoute>
                <ErrorBoundary>
                  <AppLayout />
                </ErrorBoundary>
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="scan/new" element={<NewScanPage />} />
            <Route path="scan/:id/processing" element={<ScanProcessingPage />} />
            <Route path="scan/:id" element={<ScanDetailPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="review-queue" element={<ReviewQueuePage />} />
            <Route path="reports" element={<ReportsPage />} />
            <Route path="rules" element={<RulesPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
