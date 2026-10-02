from rest_framework import viewsets
from .models import CategoriaPieza, Pieza
from .serializers import CategoriaPiezaSerializer, PiezaSerializer

class CategoriaPiezaViewSet(viewsets.ModelViewSet):
    queryset = CategoriaPieza.objects.all()
    serializer_class = CategoriaPiezaSerializer

class PiezaViewSet(viewsets.ModelViewSet):
    queryset = Pieza.objects.all()
    serializer_class = PiezaSerializer