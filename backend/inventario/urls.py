from django.urls import path, re_path

from .integraciones.views import ConsolidadoView, FacturasSedesView, LoginSedesView
from rest_framework.routers import DefaultRouter

from .views import (
    LoginView,
    MeView,
    MisComprasView,
    ReportesView,
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
    path("mis-compras/", MisComprasView.as_view(), name="mis-compras"),
    path("reportes/", ReportesView.as_view(), name="reportes"),
    # Integración entre sedes: mismas rutas y formato que la API de RepuAuto.
    re_path(r"^login/?$", LoginSedesView.as_view(), name="sedes-login"),
    re_path(r"^facturas/?$", FacturasSedesView.as_view(), name="sedes-facturas"),
    path("consolidado/", ConsolidadoView.as_view(), name="consolidado"),
]

urlpatterns += router.urls