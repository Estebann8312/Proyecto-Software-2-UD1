from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    Usuario,
    Cliente,
    CategoriaPieza,
    Pieza,
    Proveedor,
    LoteCompra,
    Venta,
)
from .permissions import (
    IsAdministrador,
    IsVendedorOrAdmin,
    LecturaEmpleadoEscrituraAdmin,
    get_empleado,
)
from .serializers import (
    UsuarioSerializer,
    ClienteSerializer,
    CategoriaPiezaSerializer,
    PiezaSerializer,
    PiezaPublicSerializer,
    ProveedorSerializer,
    LoteCompraSerializer,
    VentaSerializer,
    RegisterSerializer,
    TokenConRolSerializer,
)


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ → access, refresh y rol. Limitado contra fuerza bruta."""

    serializer_class = TokenConRolSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class RegisterView(APIView):
    """POST /api/auth/register/ → crea siempre un CLIENTE."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"message": "Cliente registrado correctamente", "username": user.username},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """GET /api/auth/me/ → datos básicos y rol del usuario autenticado (útil para el frontend)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        empleado = get_empleado(user)
        if empleado:
            rol, id_usuario, id_cliente = empleado.rol, empleado.id_usuario, None
        else:
            cliente = Cliente.objects.filter(user=user).first()
            rol, id_usuario = "cliente", None
            id_cliente = cliente.id_cliente if cliente else None
        return Response({
            "username": user.username,
            "email": user.email,
            "nombres": user.first_name,
            "apellidos": user.last_name,
            "rol": rol,
            "id_usuario": id_usuario,
            "id_cliente": id_cliente,
        })


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

class CategoriaPiezaViewSet(viewsets.ModelViewSet):
    """Lectura pública (filtros del catálogo); escritura solo administrador."""

    queryset = CategoriaPieza.objects.all().order_by("nombre")
    serializer_class = CategoriaPiezaSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdministrador()]


class PiezaViewSet(viewsets.ModelViewSet):
    """Lectura pública (catálogo reducido); empleados ven todo; escritura solo administrador."""

    queryset = (
        Pieza.objects.select_related("id_categoria")
        .prefetch_related("lotes")
        .order_by("id_pieza")
    )

    def get_serializer_class(self):
        if get_empleado(self.request.user):
            return PiezaSerializer
        return PiezaPublicSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [AllowAny()]
        return [IsAdministrador()]


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all().order_by("nombre")
    serializer_class = ProveedorSerializer
    permission_classes = [LecturaEmpleadoEscrituraAdmin]


class LoteCompraViewSet(viewsets.ModelViewSet):
    """Los lotes son el historial de entradas: solo se crean y consultan."""

    queryset = LoteCompra.objects.select_related("id_pieza", "id_proveedor").order_by("-id_lote")
    serializer_class = LoteCompraSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [IsAdministrador]



# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------

class VentaViewSet(viewsets.ModelViewSet):
    """Las ventas solo se crean, consultan y anulan (nunca se editan ni borran)."""

    queryset = (
        Venta.objects.select_related("id_cliente", "id_vendedor")
        .prefetch_related("detalles__id_pieza")
        .order_by("-fecha")
    )
    serializer_class = VentaSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_permissions(self):
        if self.action == "anular":
            return [IsAdministrador()]
        return [IsVendedorOrAdmin()]

    def perform_create(self, serializer):
        # El vendedor es SIEMPRE quien está autenticado; no se acepta desde el cliente.
        serializer.save(id_vendedor=get_empleado(self.request.user))

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        with transaction.atomic():
            # Bloqueo de la venta para evitar doble anulación simultánea.
            venta = get_object_or_404(Venta.objects.select_for_update(), pk=pk)

            if venta.estado == "anulada":
                return Response(
                    {"error": "Esta venta ya se encuentra anulada."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            venta.estado = "anulada"
            venta.save(update_fields=["estado"])

            detalles = list(venta.detalles.all())
            piezas_bloqueadas = {
                p.pk: p
                for p in Pieza.objects.select_for_update()
                .filter(pk__in=[d.id_pieza_id for d in detalles])
                .order_by("pk")
            }
            for detalle in detalles:
                pieza = piezas_bloqueadas[detalle.id_pieza_id]
                pieza.stock_actual += detalle.cantidad
                pieza.save(update_fields=["stock_actual"])

        return Response(
            {"mensaje": f"Venta {venta.id_venta} anulada exitosamente y stock devuelto."},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

class UsuarioViewSet(viewsets.ModelViewSet):
    """Gestión de empleados: exclusivamente administradores."""

    queryset = Usuario.objects.select_related("user").order_by("id_usuario")
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdministrador]

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.user_id == self.request.user.pk:
            raise ValidationError({"error": "No puedes eliminar tu propia cuenta."})
        user = instance.user
        instance.delete()  # ProtectedError (→ 409) si tiene ventas registradas
        if user is not None:
            user.delete()


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all().order_by("id_cliente")
    serializer_class = ClienteSerializer
    permission_classes = [IsVendedorOrAdmin]

    @transaction.atomic
    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()  # ProtectedError (→ 409) si tiene ventas registradas
        if user is not None:
            user.delete()  # que no quede una cuenta huérfana con acceso