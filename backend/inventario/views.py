from django.contrib.auth.hashers import check_password
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action
from django.db import transaction
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsAdministrador, IsVendedorOrAdmin, IsClienteOwner


from .models import (
    Usuario,
    Cliente,
    CategoriaPieza,
    Pieza,
    Proveedor,
    LoteCompra,
    Venta,
)
from .serializers import (
    UsuarioSerializer,
    ClienteSerializer,
    CategoriaPiezaSerializer,
    PiezaSerializer,
    ProveedorSerializer,
    LoteCompraSerializer,
    VentaSerializer,
    RegisterSerializer,
    PiezaPublicSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    "message": "Cliente registrado correctamente",
                    "username": user.username,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CategoriaPiezaViewSet(viewsets.ModelViewSet):
    queryset = CategoriaPieza.objects.all()
    serializer_class = CategoriaPiezaSerializer


class PiezaViewSet(viewsets.ModelViewSet):
    queryset = Pieza.objects.all()
    
    def get_serializer_class(self):
        # 1. Si el usuario está autenticado, comprobamos si es empleado
        if self.request.user.is_authenticated:
            email_login = self.request.user.email
            if email_login:
                try:
                    empleado = Usuario.objects.get(email__iexact=email_login)
                    if empleado.rol in ['vendedor', 'administrador']:
                        return PiezaSerializer # Administrador/Vendedor ve todo
                except Usuario.DoesNotExist:
                    pass
        
        # 2. Si es anónimo o cliente, ve el catálogo público
        return PiezaPublicSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAdministrador]
        return [permission() for permission in permission_classes]


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer


class LoteCompraViewSet(viewsets.ModelViewSet):
    queryset = LoteCompra.objects.all()
    serializer_class = LoteCompraSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    # El inventario y costos de proveedor son sensibles. Solo el Administrador ingresa lotes.
    permission_classes = [IsAdministrador]


class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer
    http_method_names = ['get', 'post', 'head', 'options']

    # Solo empleados registrados pueden registrar o anular ventas.
    # Los clientes no pueden autogenerar ventas desde la API sin pasar por el vendedor en este diseño.
    permission_classes = [IsVendedorOrAdmin]

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        # Usamos atomic para asegurar que si falla la devolución de una pieza, no se anule la venta.
        with transaction.atomic():
            # 1. Obtenemos la venta y la bloqueamos para que no puedan presionar "Anular" dos veces rápido
            venta = Venta.objects.select_for_update().get(pk=pk)

            if venta.estado == 'anulada':
                return Response(
                    {'error': 'Esta venta ya se encuentra anulada.'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 2. Cambiamos el estado de la venta
            venta.estado = 'anulada'
            venta.save(update_fields=['estado'])

            # 3. Recuperamos los detalles y bloqueamos las piezas ordenadas por PK (igual que hiciste en la creación)
            detalles = venta.detalles.all()
            piezas_ids = [detalle.id_pieza_id for detalle in detalles]
            
            piezas_bloqueadas = {
                p.pk: p for p in Pieza.objects.select_for_update().filter(pk__in=piezas_ids).order_by('pk')
            }

            # 4. Devolvemos el stock a cada pieza
            for detalle in detalles:
                pieza = piezas_bloqueadas[detalle.id_pieza_id]
                pieza.stock_actual += detalle.cantidad
                pieza.save(update_fields=['stock_actual'])

        return Response(
            {'mensaje': f'Venta {venta.id_venta} anulada exitosamente y stock devuelto.'}, 
            status=status.HTTP_200_OK
        )

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

    # Los vendedores y administradores pueden ver la lista de clientes.
    # Un cliente individual podría requerir permisos especiales más adelante.
    permission_classes = [IsVendedorOrAdmin]


class LoginUsuarioView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        if not check_password(password, usuario.password):
            return Response({'error': 'Credenciales inválidas'}, status=status.HTTP_401_UNAUTHORIZED)

        token = RefreshToken()
        token['id_usuario'] = usuario.id_usuario
        token['rol'] = usuario.rol

        return Response({
            'access': str(token.access_token),
            'id_usuario': usuario.id_usuario,
            'nombres': usuario.nombres,
            'rol': usuario.rol,
        }, status=status.HTTP_200_OK)