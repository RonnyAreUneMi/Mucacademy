from rest_framework.routers import DefaultRouter
from .views import AuditoriaViewSet

router = DefaultRouter()
router.register('', AuditoriaViewSet, basename='audit')

urlpatterns = router.urls
