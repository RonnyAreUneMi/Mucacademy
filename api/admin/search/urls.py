from django.urls import path
from .views import AdminSearchView

urlpatterns = [
    path('', AdminSearchView.as_view(), name='admin_search'),
]
