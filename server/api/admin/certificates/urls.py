from rest_framework.routers import DefaultRouter
from .views import CertificadoViewSet

router = DefaultRouter()
router.register('', CertificadoViewSet, basename='certificates')

urlpatterns = router.urls
