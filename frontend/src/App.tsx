import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { ProjectShell } from './components/layout/ProjectShell';
import { ErrorBoundary } from './app/ErrorBoundary';
import { HomePage } from './pages/HomePage';
import { LoginPage, AuthRequired } from './pages/AuthPages';
import { CheckoutPage, OrderPage, RedeemPage } from './pages/CommercePages';
import { ProjectsPage } from './pages/ProjectsPage';
import { AnalysisPage, BackgroundPage, AiPage, BaseImagePage } from './pages/ImageWorkflowPages';
import { SettingsPage } from './pages/SettingsPage';
import { ExportPage } from './pages/ExportPage';

const EditorPage = lazy(() => import('./pages/EditorPage').then((module) => ({ default: module.EditorPage })));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
  },
});

function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/orders/:orderId" element={<AuthRequired><OrderPage /></AuthRequired>} />
          <Route path="/redeem" element={<RedeemPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<Navigate to="analysis" replace />} />
          <Route path="/projects/:projectId" element={<ProjectShell />}>
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="background" element={<BackgroundPage />} />
            <Route path="ai" element={<AiPage />} />
            <Route path="base-image" element={<BaseImagePage />} />
            <Route path="settings" element={<SettingsPage />} />
            <Route path="editor" element={<Suspense fallback={<div className="app-loading"><div className="spinner" /></div>}><EditorPage /></Suspense>} />
            <Route path="export" element={<ExportPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default function App() {
  return <ErrorBoundary><QueryClientProvider client={queryClient}><AppRoutes /></QueryClientProvider></ErrorBoundary>;
}
