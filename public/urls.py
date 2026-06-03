"""URLs públicas — landing + flujo guest + cuentas de participantes.

La lógica de los flujos guest (cédula, hash de cert, QR) sigue en
`api/public/*`. Las páginas con server-side state (login, register,
mis-certificados, eventos personalizados) viven en `public.views`.
"""
from django.urls import path
from django.views.generic import RedirectView, TemplateView

from . import views as account_views

app_name = 'public'


def page(template):
    return TemplateView.as_view(template_name=template)


urlpatterns = [
    # ── Landing rediseñada (con datos de eventos para hero/swiper) ──
    path('', account_views.home, name='home'),
    path('inicio/', RedirectView.as_view(pattern_name='public:home', permanent=False), name='inicio_legacy'),

    # ── Cuenta de participante ──────────────────────────────
    path('cuenta/login/',         account_views.login_view,        name='account_login'),
    path('cuenta/register/',      account_views.register_view,     name='account_register'),
    path('cuenta/logout/',        account_views.logout_view,       name='account_logout'),
    path('cuenta/',               account_views.dashboard,         name='account_dashboard'),
    path('cuenta/certificados/',  account_views.certificados_view, name='account_certificados'),
    path('cuenta/eventos/',       account_views.eventos_view,      name='account_eventos'),
    path('cuenta/perfil/',        account_views.perfil_view,       name='account_perfil'),
    path('cuenta/eventos/<int:sesion_id>/inscribir/',
         account_views.evento_inscribir, name='account_evento_inscribir'),
    path('cuenta/eventos/<int:sesion_id>/resumen/',
         account_views.evento_resumen_view, name='account_evento_resumen'),
    path('cuenta/eventos/<int:sesion_id>/resumen/pdf/',
         account_views.evento_resumen_pdf_view, name='account_evento_resumen_pdf'),
    path('cuenta/eventos/<int:sesion_id>/cuestionario/',
         account_views.evento_cuestionario_view, name='account_evento_cuestionario'),
    path('cuenta/eventos/<int:sesion_id>/cuestionario/submit/',
         account_views.evento_cuestionario_submit, name='account_evento_cuestionario_submit'),
    path('cuenta/escanear/',           account_views.escanear_view,      name='account_escanear'),
    path('cuenta/escanear/registrar/', account_views.escanear_registrar, name='account_escanear_registrar'),

    # ── Recuperación de contraseña ──────────────────────────
    path('cuenta/recuperar/',              account_views.password_reset_request,     name='account_password_reset_request'),
    path('cuenta/recuperar/enviado/',      account_views.password_reset_sent,        name='account_password_reset_sent'),
    path('cuenta/recuperar/codigo/',       account_views.password_reset_verify_code, name='account_password_reset_verify_code'),
    path('cuenta/recuperar/r/<uuid:token>/', account_views.password_reset_link,      name='account_password_reset_link'),
    path('cuenta/recuperar/nueva/',        account_views.password_reset_new,         name='account_password_reset_new'),
    path('cuenta/recuperar/status/',       account_views.password_reset_status,      name='account_password_reset_status'),

    # ── Google Sign-In ──────────────────────────────────────
    path('cuenta/google/start/',    account_views.google_signin_start,    name='account_google_start'),
    path('cuenta/google/callback/', account_views.google_signin_callback, name='account_google_callback'),

    path('eventos/', page('public/eventos_list.html'), name='eventos_disponibles'),
    path('search/', page('public/search.html'), name='search'),
    path('attendance/', page('public/attendance_search.html'), name='attendance_search'),
    path('attendance/verify/', page('public/attendance_verify.html'), name='attendance_verify'),
    path('sesion/<int:id>/registro/', page('public/session_register.html'), name='session_register'),
    path('checkin/<str:codigo_qr>/', page('public/qr_checkin.html'), name='qr_checkin'),
    path('verificar/<str:hash>/', page('public/verify_certificate.html'), name='verify_certificate'),

    # ── Redirects legacy → API ───────────────────────────────
    path('download/<str:hash>/',
         RedirectView.as_view(url='/api/v1/public/certificates/%(hash)s/download/', permanent=False),
         name='download_pdf'),
    path('download-all/',
         RedirectView.as_view(url='/api/v1/public/certificates/bulk-download/', query_string=True, permanent=False),
         name='download_zip'),
    path('search/autocomplete/',
         RedirectView.as_view(url='/api/v1/public/certificates/autocomplete/', query_string=True, permanent=False),
         name='search_autocomplete'),
    path('attendance/autocomplete/',
         RedirectView.as_view(url='/api/v1/public/attendance/search/', query_string=True, permanent=False),
         name='attendance_autocomplete'),
    path('attendance/sessions/',
         RedirectView.as_view(url='/api/v1/public/attendance/sessions/', permanent=False),
         name='attendance_sessions_api'),
    path('attendance/confirm/',
         RedirectView.as_view(url='/api/v1/public/attendance/confirm/', permanent=False),
         name='attendance_confirm'),
    path('attendance/update-phone/',
         RedirectView.as_view(url='/api/v1/public/attendance/update-phone/', permanent=False),
         name='attendance_update_phone'),
    path('sesion/<int:id>/registro/buscar/',
         RedirectView.as_view(url='/api/v1/public/sessions/%(id)s/search-participant/', query_string=True, permanent=False),
         name='session_register_search'),
    path('sesion/<int:id>/registro/confirmar/',
         RedirectView.as_view(url='/api/v1/public/sessions/%(id)s/confirm-participant/', permanent=False),
         name='session_register_confirm'),
    path('sesion/<int:id>/registro/nuevo/',
         RedirectView.as_view(url='/api/v1/public/sessions/%(id)s/register-participant/', permanent=False),
         name='session_register_new'),
    path('checkin/<str:codigo_qr>/search/',
         RedirectView.as_view(url='/api/v1/public/checkin/%(codigo_qr)s/search/', query_string=True, permanent=False),
         name='qr_checkin_search'),
    path('checkin/<str:codigo_qr>/register/',
         RedirectView.as_view(url='/api/v1/public/checkin/%(codigo_qr)s/register/', permanent=False),
         name='qr_checkin_register'),
]
