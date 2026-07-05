from django.urls import path
from .views import (
    AttendanceSearchView, AttendanceVerifyView,
    AttendanceSessionsView, AttendanceConfirmView, AttendanceUpdatePhoneView,
)

urlpatterns = [
    path('search/', AttendanceSearchView.as_view(), name='attendance-search'),
    path('verify/', AttendanceVerifyView.as_view(), name='attendance-verify'),
    path('sessions/', AttendanceSessionsView.as_view(), name='attendance-sessions'),
    path('confirm/', AttendanceConfirmView.as_view(), name='attendance-confirm'),
    path('update-phone/', AttendanceUpdatePhoneView.as_view(), name='attendance-update-phone'),
]
