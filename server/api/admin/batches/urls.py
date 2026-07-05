from rest_framework.routers import DefaultRouter
from .views import LoteViewSet

router = DefaultRouter()
router.register('', LoteViewSet, basename='batches')

urlpatterns = router.urls
