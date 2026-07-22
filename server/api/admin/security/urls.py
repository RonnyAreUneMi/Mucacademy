from django.urls import path

from .views import SecurityMatrixView

urlpatterns = [
    path('matrix/', SecurityMatrixView.as_view(), name='security_matrix'),
]
