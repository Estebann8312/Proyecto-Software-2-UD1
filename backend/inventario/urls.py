from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    RegisterView,
    LoginUsuarioView,
    UsuarioViewSet,
    ClienteViewSet,
    CategoriaPiezaViewSet,
    PiezaViewSet,
    ProveedorViewSet,
    LoteCompraViewSet,
    VentaViewSet,
)

router = DefaultRouter()

router.register(r"usuarios", UsuarioViewSet)
router.register(r"clientes", ClienteViewSet)
router.register(r"categorias", CategoriaPiezaViewSet)
router.register(r"piezas", PiezaViewSet)
router.register(r"proveedores", ProveedorViewSet)
router.register(r"lotes", LoteCompraViewSet)
router.register(r"ventas", VentaViewSet)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginUsuarioView.as_view(), name="login"),
]

urlpatterns += router.urls
