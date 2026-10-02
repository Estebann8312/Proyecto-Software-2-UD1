from rest_framework.routers import DefaultRouter
from .views import CategoriaPiezaViewSet, PiezaViewSet

router = DefaultRouter()
router.register(r'categorias', CategoriaPiezaViewSet)
router.register(r'piezas', PiezaViewSet)

urlpatterns = router.urls