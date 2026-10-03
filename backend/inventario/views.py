from rest_framework import viewsets
from .models import CategoriaPieza, Pieza, Proveedor, LoteCompra, Venta, DetalleVenta
from .serializers import (
    CategoriaPiezaSerializer, PiezaSerializer,
    ProveedorSerializer, LoteCompraSerializer, VentaSerializer
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