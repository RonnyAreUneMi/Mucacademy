from django.urls import path

from . import views

urlpatterns = [
    path('', views.PublicProgramListView.as_view(), name='public-programs'),
    path('<int:program_id>/', views.PublicProgramDetailView.as_view(), name='public-program-detail'),
]
