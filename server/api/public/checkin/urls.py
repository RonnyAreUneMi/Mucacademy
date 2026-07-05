from django.urls import path
from .views import CheckinSessionView, CheckinSearchView, CheckinRegisterView

urlpatterns = [
    path('<str:codigo_qr>/session/', CheckinSessionView.as_view(), name='checkin-session'),
    path('<str:codigo_qr>/search/', CheckinSearchView.as_view(), name='checkin-search'),
    path('<str:codigo_qr>/register/', CheckinRegisterView.as_view(), name='checkin-register'),
]
