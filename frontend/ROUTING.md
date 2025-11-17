# Frontend Routing

React Router v6 is configured with the following routes:

## Public Routes (Unauthenticated Only)

These routes are accessible only when NOT logged in. Authenticated users are redirected to `/dashboard`.

- **`/login`** - Login page with email/password authentication
- **`/register`** - User registration page (UI only, needs backend integration)

## Protected Routes (Authentication Required)

All routes require authentication (valid JWT token in localStorage). Unauthenticated users are redirected to `/login`.

- **`/dashboard`** - Main dashboard (requires authentication)
- **`/`** - Root path (redirects to `/dashboard` if authenticated, otherwise to `/login`)
- **`*`** (catch-all) - Any unmatched route (redirects to `/dashboard` if authenticated, otherwise to `/login`)

## Authentication Flow

1. **Unauthenticated users**:
   - Accessing `/` or any protected route → redirected to `/login`
   - Accessing `/login` or `/register` → allowed

2. **Authenticated users**:
   - Accessing `/login` or `/register` → redirected to `/dashboard`
   - Accessing `/` or any protected route → allowed
   - Accessing unknown routes → redirected to `/dashboard`

3. **Login process**:
   - Successful login → stores JWT tokens → redirects to `/dashboard`

4. **Token expiry**:
   - Auto-refresh attempted on 401 errors
   - If refresh fails → tokens cleared → redirected to `/login`

5. **Logout**:
   - Clears tokens → redirects to `/login`

## Key Components

- **`ProtectedRoute`** - Wrapper that checks for authentication, redirects to `/login` if not authenticated
- **`PublicRoute`** - Wrapper that redirects to `/dashboard` if already authenticated
- **`LoginForm`** - Handles login with backend `/api/auth/token/` endpoint
- **`DashboardPage`** - Protected dashboard with user info and logout

## Navigation

All navigation uses React Router's `<Link>` and `useNavigate()` hook for client-side routing without page reloads.

## API Integration

- Login: `POST /api/auth/token/` → returns `{ access, refresh }`
- User info: `GET /api/v1/users/me/` (with Bearer token)
- Token refresh: `POST /api/auth/token/refresh/` (automatic on 401)
