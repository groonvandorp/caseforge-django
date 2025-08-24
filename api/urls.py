from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'models', views.ProcessModelViewSet, basename='processmodel')
router.register(r'versions', views.ProcessModelVersionViewSet, basename='processmodelversion')
router.register(r'nodes', views.ProcessNodeViewSet, basename='processnode')
router.register(r'documents', views.NodeDocumentViewSet, basename='nodedocument')
router.register(r'usecases', views.NodeUsecaseCandidateViewSet, basename='nodeusecasecandidate')
router.register(r'bookmarks', views.NodeBookmarkViewSet, basename='nodebookmark')
router.register(r'portfolios', views.PortfolioViewSet, basename='portfolio')

urlpatterns = [
    # Authentication
    path('auth/signup/', views.signup, name='signup'),
    path('auth/token/', views.token, name='token'),
    path('auth/me/', views.me, name='me'),
    
    # Dashboard
    path('dashboard/specs/', views.dashboard_specs, name='dashboard_specs'),
    
    # User settings
    path('settings/', views.user_settings_view, name='user_settings'),
    path('settings/update/', views.update_user_settings, name='update_user_settings'),
    
    # API routes
    path('', include(router.urls)),
]