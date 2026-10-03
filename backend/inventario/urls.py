from rest_framework.routers import DefaultRouter
from .views import CategoriaPiezaViewSet, PiezaViewSet, ProveedorViewSet, LoteCompraViewSet


router = DefaultRouter()
router.register(r'categorias', CategoriaPiezaViewSet)
router.register(r'piezas', PiezaViewSet)
router.register(r'proveedores', ProveedorViewSet)
router.register(r'lotes', LoteCompraViewSet)

urlpatterns = router.urls