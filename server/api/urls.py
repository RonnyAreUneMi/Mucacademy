from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

app_name = 'api'

urlpatterns = [
    # Auth (compartido)
    path('v1/auth/', include('api.auth.urls')),

    # Admin (requiere auth + permisos de staff/superadmin)
    path('v1/admin/', include('api.admin.urls')),

    # Público (read-only, sin auth o con throttling)
    path('v1/public/', include('api.public.urls')),

    # Docs
    path('v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('v1/docs/', SpectacularSwaggerView.as_view(url_name='api:schema'), name='docs'),
    path('v1/redoc/', SpectacularRedocView.as_view(url_name='api:schema'), name='redoc'),
]
