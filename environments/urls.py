from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnvironmentViewSet,
    EnvironmentListView,
    EnvironmentDetailView,
    EnvironmentCreateView,
    EnvironmentUpdateView,
    EnvironmentDeleteView,
    check_port_available
)

router = DefaultRouter()
router.register(r'environments', EnvironmentViewSet)

urlpatterns = [
    # API URLs
    path('api/', include(router.urls)),
    
    # Template URLs
    path('check-port/', check_port_available, name='check_port'),
    path('', EnvironmentListView.as_view(), name='environment_list'),
    path('create/', EnvironmentCreateView.as_view(), name='environment_create'),
    path('<int:pk>/', EnvironmentDetailView.as_view(), name='environment_detail'),
    path('<int:pk>/edit/', EnvironmentUpdateView.as_view(), name='environment_update'),
    path('<int:pk>/delete/', EnvironmentDeleteView.as_view(), name='environment_delete'),
    
    # Environment Actions (non-API)
    path('environments/<int:pk>/start/', EnvironmentViewSet.as_view({'post': 'start'}), name='environment_start'),
    path('environments/<int:pk>/stop/', EnvironmentViewSet.as_view({'post': 'stop'}), name='environment_stop'),
]
