"""
Endpoints de la integración entre sedes.

POST /api/login       {"correo", "clave"} → token (solo administradores). Igual al de RepuAuto.
GET  /api/facturas    ?desde&hasta&tipo   → facturas de esta sede en el formato acordado.
GET  /api/inventario  ?estado             → inventario de esta sede en el formato acordado.
GET  /api/consolidado/ ?desde&hasta       → facturas de las dos sedes (para nuestro frontend).
GET  /api/consolidado/inventario/         → inventario de las dos sedes (para nuestro frontend).

/api/login, /api/facturas y /api/inventario imitan a RepuAuto también en los errores:
siempre {"error": "..."}.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import AccessToken

from ..autenticacion import ALCANCE_INTEGRACION
from ..permissions import IsAdministrador, get_empleado
from . import consolidado, facturas, inventario

User = get_user_model()


def error(mensaje, codigo):
    return Response({"error": mensaje}, status=codigo)


class VistaFormatoSedes(APIView):
    """Convierte los errores de DRF ({"detail": ...}) al formato acordado ({"error": ...})."""

    def handle_exception(self, exc):
        respuesta = super().handle_exception(exc)
        if isinstance(respuesta.data, dict) and "detail" in respuesta.data:
            respuesta.data = {"error": str(respuesta.data["detail"])}
        return respuesta


class LoginSedesView(VistaFormatoSedes):
    """Inicio de sesión para otros sistemas. El token sirve como Bearer en /api/facturas."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        datos = request.data if isinstance(request.data, dict) else {}
        correo, clave = datos.get("correo"), datos.get("clave")
        if not isinstance(correo, str) or not isinstance(clave, str) or not correo.strip() or not clave:
            return error('Envía un JSON con "correo" y "clave".', status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=correo.strip()).first()
        if user is None or not user.is_active or not user.check_password(clave):
            return error("Correo o contraseña incorrectos.", status.HTTP_401_UNAUTHORIZED)
        empleado = get_empleado(user)
        if empleado is None or empleado.rol != "administrador":
            return error("Solo un administrador puede usar la API.", status.HTTP_403_FORBIDDEN)

        horas = settings.INTEGRACION["TOKEN_HORAS"]
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=timedelta(hours=horas))
        token["rol"] = empleado.rol
        token["alcance"] = ALCANCE_INTEGRACION
        return Response({
            "token": str(token),
            "tipo": "Bearer",
            "expira_en": int(horas * 3600),
            "usuario": {"nombre": f"{empleado.nombres} {empleado.apellidos}", "rol": empleado.rol},
        })


class VistaLecturaSedes(VistaFormatoSedes):
    """Lectura para la otra sede. Acepta el token de /api/login (que solo sirve aquí)
    y el token normal del frontend, siempre de un administrador."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAdministrador]

    def permission_denied(self, request, message=None, code=None):
        if request.user and request.user.is_authenticated:
            message = "Solo un administrador puede usar la API."
        super().permission_denied(request, message=message, code=code)


class FacturasSedesView(VistaLecturaSedes):
    """Facturas de esta sede para el consolidador."""

    def get(self, request):
        tipo = request.query_params.get("tipo", "").strip().lower() or None
        if tipo is not None and tipo not in facturas.TIPOS:
            return error('El tipo debe ser "venta" o "compra", o no enviarlo para traer las dos.',
                         status.HTTP_400_BAD_REQUEST)
        try:
            desde, hasta = facturas.leer_rango(
                request.query_params.get("desde", "").strip(), request.query_params.get("hasta", "").strip()
            )
        except facturas.RangoInvalido as e:
            return error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(facturas.facturas(desde, hasta, tipo))


class InventarioSedesView(VistaLecturaSedes):
    """Inventario de hoy de esta sede, con el formato de RepuAuto."""

    def get(self, request):
        try:
            estado = inventario.leer_estado(request.query_params.get("estado"))
        except inventario.EstadoInvalido as e:
            return error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(inventario.inventario(estado))


class ConsolidadoView(APIView):
    """Las dos sedes juntas, para la pantalla del administrador."""

    permission_classes = [IsAdministrador]

    def get(self, request):
        try:
            desde, hasta = facturas.leer_rango(
                request.query_params.get("desde", "").strip(), request.query_params.get("hasta", "").strip()
            )
        except facturas.RangoInvalido as e:
            return error(str(e), status.HTTP_400_BAD_REQUEST)
        return Response(consolidado.consolidar(desde, hasta))


class ConsolidadoInventarioView(APIView):
    """Inventario de hoy de las dos sedes, para la pantalla del administrador."""

    permission_classes = [IsAdministrador]

    def get(self, request):
        return Response(consolidado.consolidar_inventario())
