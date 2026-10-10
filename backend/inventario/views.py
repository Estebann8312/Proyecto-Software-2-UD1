from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password

from rest_framework import viewsets
from .models import CategoriaPieza, Pieza, Proveedor, LoteCompra, Venta, DetalleVenta, Usuario, Cliente
from .serializers import (
    CategoriaPiezaSerializer, PiezaSerializer,
    ProveedorSerializer, LoteCompraSerializer, VentaSerializer, UsuarioSerializer, ClienteSerializer
)


class CategoriaPiezaViewSet(viewsets.ModelViewSet):
    queryset = CategoriaPieza.objects.all()
    serializer_class = CategoriaPiezaSerializer

class PiezaViewSet(viewsets.ModelViewSet):
    queryset = Pieza.objects.all()
    serializer_class = PiezaSerializer

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer

class LoteCompraViewSet(viewsets.ModelViewSet):
    queryset = LoteCompra.objects.all()
    serializer_class = LoteCompraSerializer

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.all()
    serializer_class = UsuarioSerializer


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer


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