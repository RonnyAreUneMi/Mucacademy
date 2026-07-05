from rest_framework.routers import DefaultRouter
from .views import FirmaViewSet

router = DefaultRouter()
router.register('', FirmaViewSet, basename='firmas')

urlpatterns = router.urls
