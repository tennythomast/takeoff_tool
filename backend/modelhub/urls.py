from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'providers', views.ProviderViewSet)
router.register(r'models', views.ModelViewSet)
router.register(r'api-keys', views.APIKeyViewSet)
router.register(r'routing-rules', views.RoutingRuleViewSet)
router.register(r'metrics', views.ModelMetricsViewSet)

app_name = 'modelhub'

urlpatterns = [
    path('', include(router.urls)),
    # Temporarily commenting out routing analytics views until they are implemented
    # path('routing/analytics/cost-savings/', views.RoutingCostSavingsView.as_view(), name='routing-cost-savings'),
    # path('routing/analytics/performance/', views.RoutingPerformanceView.as_view(), name='routing-performance'),
    # path('routing/analytics/recommendations/', views.RoutingRecommendationsView.as_view(), name='routing-recommendations'),
    # path('routing/session/<str:session_id>/info/', views.SessionRoutingInfoView.as_view(), name='session-routing-info'),
    # path('routing/test/', views.TestRoutingView.as_view(), name='test-routing'),
]
