import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import { ProtectedRoute } from './components/ProtectedRoute'
import { PublicRoute } from './components/PublicRoute'
import { Toaster } from '@/components/ui/toaster'
import { AppLayout } from '@/components/app-layout'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes - redirect to dashboard if already logged in */}
        <Route
          path="/login"
          element={
            <PublicRoute>
              <LoginPage />
            </PublicRoute>
          }
        />
        <Route
          path="/register"
          element={
            <PublicRoute>
              <RegisterPage />
            </PublicRoute>
          }
        />

        {/* Protected routes - require authentication and use AppLayout */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DashboardPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />

        {/* Workspace route - placeholder for future implementation */}
        <Route
          path="/workspace"
          element={
            <ProtectedRoute>
              <AppLayout>
                <div className="flex h-full items-center justify-center p-6">
                  <div className="text-center">
                    <h2 className="text-2xl font-bold">Workspace</h2>
                    <p className="text-muted-foreground mt-2">
                      Workspace functionality coming soon
                    </p>
                  </div>
                </div>
              </AppLayout>
            </ProtectedRoute>
          }
        />

        {/* Root path - redirect based on auth status */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Navigate to="/dashboard" replace />
            </ProtectedRoute>
          }
        />

        {/* Catch all - redirect to dashboard (will redirect to login if not authenticated) */}
        <Route
          path="*"
          element={
            <ProtectedRoute>
              <Navigate to="/dashboard" replace />
            </ProtectedRoute>
          }
        />
      </Routes>
      <Toaster />
    </BrowserRouter>
  )
}

export default App
