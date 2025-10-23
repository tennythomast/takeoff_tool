# /backend/file_storage/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FileStorageBackendViewSet, FileUploadViewSet, FileProcessingJobViewSet, FileFolderViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'files', FileUploadViewSet, basename='file')
router.register(r'folders', FileFolderViewSet, basename='folder')
router.register(r'storage-backends', FileStorageBackendViewSet, basename='storage-backend')
router.register(r'processing-jobs', FileProcessingJobViewSet, basename='processing-job')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]