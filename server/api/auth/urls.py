from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenBlacklistView
from .register import RegisterView
from .views import LoginView, MeView

urlpatterns = [
    path('login/', LoginView.as_view(), name='api_login'),
    path('refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('logout/', TokenBlacklistView.as_view(), name='api_logout'),
    path('me/', MeView.as_view(), name='api_me'),
    path('register/', RegisterView.as_view(), name='api_register'),
]
