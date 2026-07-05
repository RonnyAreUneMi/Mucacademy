from rest_framework.routers import DefaultRouter
from .views import PublicSesionViewSet

router = DefaultRouter()
router.register('', PublicSesionViewSet, basename='public-sessions')

urlpatterns = router.urls
