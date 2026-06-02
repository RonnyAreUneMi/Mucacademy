from django.urls import path

from . import views

urlpatterns = [
    # Público (sin auth)
    path('landing/', views.LandingView.as_view(), name='mobile-landing'),

    # Auth
    path('login/',    views.LoginView.as_view(),    name='mobile-login'),
    path('register/', views.RegisterView.as_view(), name='mobile-register'),
    path('logout/',   views.LogoutView.as_view(),   name='mobile-logout'),

    # Cuenta
    path('me/',           views.MeView.as_view(),           name='mobile-me'),
    path('dashboard/',    views.DashboardView.as_view(),    name='mobile-dashboard'),
    path('certificates/', views.CertificadosView.as_view(), name='mobile-certificates'),
    path('events/',                          views.EventosView.as_view(),         name='mobile-events'),
    path('events/<int:event_id>/',           views.EventoDetailView.as_view(),    name='mobile-event-detail'),
    path('events/<int:event_id>/register/',  views.InscribirEventoView.as_view(), name='mobile-event-register'),
    path('attendances/',                     views.AsistenciasView.as_view(),     name='mobile-attendances'),
    path('checkin/',                         views.CheckinByQRView.as_view(),     name='mobile-checkin-qr'),
]
