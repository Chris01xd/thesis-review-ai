import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './contexts/AuthContext'
import { ErrorBoundary } from './components/shared/ErrorBoundary'
import { ProtectedRoute } from './components/shared/ProtectedRoute'
import { AppLayout } from './components/layout/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import StudentsPage from './pages/StudentsPage'
import AdvancesPage from './pages/AdvancesPage'
import AdvanceDetailPage from './pages/AdvanceDetailPage'
import UploadPage from './pages/UploadPage'
import HumanReviewPage from './pages/HumanReviewPage'
import BatchReviewPage from './pages/BatchReviewPage'
import StatisticsPage from './pages/StatisticsPage'
import ReportsPage from './pages/ReportsPage'
import TemplatesPage from './pages/TemplatesPage'
import UsersPage from './pages/UsersPage'
import AuditPage from './pages/AuditPage'
import ConfigPage from './pages/ConfigPage'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 30_000 } },
})

export default function App() {
  return (
    <ErrorBoundary>
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DashboardPage />} />
              <Route path="students" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR', 'ADVISOR']}>
                  <StudentsPage />
                </ProtectedRoute>
              } />
              <Route path="advances" element={<AdvancesPage />} />
              <Route path="advances/:id" element={<AdvanceDetailPage />} />
              <Route path="upload" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR', 'ADVISOR']}>
                  <UploadPage />
                </ProtectedRoute>
              } />
              <Route path="review" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR', 'ADVISOR']}>
                  <HumanReviewPage />
                </ProtectedRoute>
              } />
              <Route path="batch" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR', 'ADVISOR']}>
                  <BatchReviewPage />
                </ProtectedRoute>
              } />
              <Route path="statistics" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR', 'ADVISOR']}>
                  <StatisticsPage />
                </ProtectedRoute>
              } />
              <Route path="reports" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR', 'ADVISOR']}>
                  <ReportsPage />
                </ProtectedRoute>
              } />
              <Route path="templates" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR']}>
                  <TemplatesPage />
                </ProtectedRoute>
              } />
              <Route path="users" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR']}>
                  <UsersPage />
                </ProtectedRoute>
              } />
              <Route path="audit" element={
                <ProtectedRoute roles={['ADMIN', 'COORDINATOR']}>
                  <AuditPage />
                </ProtectedRoute>
              } />
              <Route path="config" element={
                <ProtectedRoute roles={['ADMIN']}>
                  <ConfigPage />
                </ProtectedRoute>
              } />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
    </ErrorBoundary>
  )
}
