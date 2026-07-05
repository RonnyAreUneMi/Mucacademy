from rest_framework.routers import DefaultRouter
from .views import SesionViewSet

router = DefaultRouter()
router.register('', SesionViewSet, basename='sessions')

urlpatterns = router.urls
