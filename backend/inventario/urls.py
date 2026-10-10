from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    CategoriaPiezaViewSet, PiezaViewSet, ProveedorViewSet,
    LoteCompraViewSet, VentaViewSet, UsuarioViewSet, ClienteViewSet,
    LoginUsuarioView)


router = DefaultRouter()
router.register(r'categorias', CategoriaPiezaViewSet)
router.register(r'piezas', PiezaViewSet)
router.register(r'proveedores', ProveedorViewSet)
router.register(r'lotes', LoteCompraViewSet)
router.register(r'ventas', VentaViewSet)
router.register(r'usuarios', UsuarioViewSet)
router.register(r'clientes', ClienteViewSet)

urlpatterns = router.urls + [
    path('login/usuario/', LoginUsuarioView.as_view(), name='login_usuario'),
]