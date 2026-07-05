from django.urls import path

from . import views
from . import evaluations as eval_views

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
    path('programs/<int:program_id>/enroll/', views.ProgramEnrollView.as_view(),  name='mobile-program-enroll'),

    # Evaluaciones (rendir)
    path('evaluations/',                        eval_views.EvaluationsListView.as_view(),  name='mobile-evaluations'),
    path('evaluations/<int:evaluation_id>/',    eval_views.EvaluationDetailView.as_view(), name='mobile-evaluation-detail'),
    path('evaluations/<int:evaluation_id>/submit/', eval_views.EvaluationSubmitView.as_view(), name='mobile-evaluation-submit'),
]
