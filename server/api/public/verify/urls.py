from django.urls import path
from .views import VerifyCertificateView

urlpatterns = [
    path('<str:hash>/', VerifyCertificateView.as_view(), name='verify-certificate'),
]
