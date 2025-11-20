from django.urls import path
from rest_framework.routers import DefaultRouter

# For now, create an empty router since we're removing workspace dependencies
router = DefaultRouter()

# Include all router URLs
urlpatterns = router.urls
