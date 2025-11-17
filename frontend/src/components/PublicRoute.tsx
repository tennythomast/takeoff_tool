import { Navigate } from 'react-router-dom'

interface PublicRouteProps {
  children: React.ReactNode
}

export function PublicRoute({ children }: PublicRouteProps) {
  const token = localStorage.getItem('access_token')

  if (token) {
    // If user is already logged in, redirect to dashboard
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
