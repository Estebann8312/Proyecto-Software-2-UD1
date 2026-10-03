from rest_framework import serializers
from .models import CategoriaPieza, Pieza, Proveedor, LoteCompra


class CategoriaPiezaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaPieza
        fields = '__all__'

class PiezaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pieza
        fields = '__all__'

class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'

class LoteCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoteCompra
        fields = '__all__'