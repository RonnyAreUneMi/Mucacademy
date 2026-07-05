from django.urls import path
from .views import DisenoGlobalView

urlpatterns = [
    path('global/', DisenoGlobalView.as_view(), name='design_global'),
]
