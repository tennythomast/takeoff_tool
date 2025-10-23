"""
URL configuration for dataelan workspace.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoworkspace.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.conf.urls.static import static
from core.views import health_check, CreateUserView, CurrentUserView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView
)
from core.views.auth import EmailTokenObtainPairView

# API v1 patterns
api_v1_patterns = [
    path('', include('core.urls')),  # Core app - organizations, users, etc.
    path('', include('workspaces.urls')),
    path('', include('prompt.urls')),
    path('', include('file_storage.urls')),
    path('', include('modelhub.urls')),  # Model provider management
    path('', include('agents.urls')),  # Agent management
    path('mcp/', include('mcp.urls')),  # Model Control Plane management
    path('context/', include('context_manager.urls')),  # Context and knowledge management
]

# Main URL patterns
urlpatterns = [
    # Override the admin login view with a CSRF-exempt version for development
    path('admin/login/', csrf_exempt(LoginView.as_view(template_name='admin/login.html')), name='admin-login'),
    path('admin/', admin.site.urls),
    
    # API endpoints
    path('api/v1/', include((api_v1_patterns, 'v1'))),
    
    # Health check endpoints (both paths for compatibility)
    path('api/health/', health_check, name='health_check'),
    path('api/health-check/', health_check, name='health_check_alt'),
    
    # Authentication endpoints
    path('api/auth/token/', EmailTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/register/', CreateUserView.as_view(), name='user_register'),
    
    # API v1 user endpoints - for frontend compatibility
    path('api/v1/users/', CreateUserView.as_view(), name='user_register_v1'),
    path('api/v1/users/me/', CurrentUserView.as_view(), name='current_user'),
    path('api/', include('workspaces.urls')),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI - choose either Swagger or Redoc
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Serve temporary storage files
    urlpatterns += static(settings.TEMP_STORAGE_URL, document_root=settings.TEMP_STORAGE_ROOT)
