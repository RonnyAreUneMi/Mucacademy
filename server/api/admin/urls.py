"""URLs de administración — todas requieren autenticación admin."""
from django.urls import include, path

from api.admin.evaluations.urls import evaluations_router, questions_router

urlpatterns = [
    path('dashboard/', include('api.admin.dashboard.urls')),
    path('sessions/', include('api.admin.sessions.urls')),
    path('programs/', include('api.admin.programs.urls')),
    path('evaluations/', include(evaluations_router.urls)),
    path('evaluation-questions/', include(questions_router.urls)),
    path('search/', include('api.admin.search.urls')),
    path('batches/', include('api.admin.batches.urls')),
    path('participants/', include('api.admin.participants.urls')),
    path('certificates/', include('api.admin.certificates.urls')),
    path('users/', include('api.admin.users.urls')),
    path('audit/', include('api.admin.audit.urls')),
    path('firmas/', include('api.admin.firmas.urls')),
    path('design/', include('api.admin.design.urls')),
    path('ai/', include('api.admin.ai.urls')),
    path('security/', include('api.admin.security.urls')),
]
