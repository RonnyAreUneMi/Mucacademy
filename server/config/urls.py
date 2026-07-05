from django.contrib import admin
from django.urls import path, re_path, include
from django.views.generic import TemplateView
from django.views.static import serve as _media_serve
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


urlpatterns = [
    path('admin/', admin.site.urls),

    # API REST (JSON)
    path('api/', include('api.urls')),

    # ── Documentación OpenAPI / Swagger ─────────────────────────
    path('api/schema/',         SpectacularAPIView.as_view(),     name='schema'),
    path('api/docs/',           SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/',          SpectacularRedocView.as_view(url_name='schema'),   name='redoc'),

    # Admin Panel (Django MVC)
    path('panel/', include(('admin_panel.urls', 'admin_panel'), namespace='panel')),

    # Páginas públicas (shells HTML — la lógica vive en /api/v1/public/)
    path('', include('public.urls')),

    # Templates de error (debug)
    path('test-400/', TemplateView.as_view(template_name='400.html')),
    path('test-403/', TemplateView.as_view(template_name='403.html')),
    path('test-404/', TemplateView.as_view(template_name='404.html')),
    path('test-500/', TemplateView.as_view(template_name='500.html')),

    # Media (banners, PDFs, avatars). El helper static() solo sirve en DEBUG;
    # esta ruta sirve /media/ también en producción/Docker (disco local).
    re_path(r'^media/(?P<path>.*)$', _media_serve, {'document_root': settings.MEDIA_ROOT}),
]
