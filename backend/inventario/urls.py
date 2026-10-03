from rest_framework.routers import DefaultRouter
from .views import CategoriaPiezaViewSet, PiezaViewSet, ProveedorViewSet, LoteCompraViewSet, VentaViewSet


router = DefaultRouter()
router.register(r'categorias', CategoriaPiezaViewSet)
router.register(r'piezas', PiezaViewSet)
router.register(r'proveedores', ProveedorViewSet)
router.register(r'lotes', LoteCompraViewSet)
router.register(r'ventas', VentaViewSet)

urlpatterns = router.urls