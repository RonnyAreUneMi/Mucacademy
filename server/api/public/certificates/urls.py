from rest_framework.routers import DefaultRouter
from .views import PublicCertificadoViewSet

router = DefaultRouter()
router.register('', PublicCertificadoViewSet, basename='public-certificates')

urlpatterns = router.urls
