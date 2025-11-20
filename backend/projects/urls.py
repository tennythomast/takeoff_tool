from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from .views import ProjectViewSet, ProjectCollaboratorViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project')

# Create nested router for project collaborators
projects_router = routers.NestedDefaultRouter(router, r'projects', lookup='project')
projects_router.register(r'collaborators', ProjectCollaboratorViewSet, basename='project-collaborators')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(projects_router.urls)),
]
