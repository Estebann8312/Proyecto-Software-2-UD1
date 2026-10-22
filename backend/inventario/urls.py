from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    MeView,
    RegisterView,
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
    path("auth/login/", LoginView.as_view(), name="token_obtain_pair"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/me/", MeView.as_view(), name="me"),
]

urlpatterns += router.urls