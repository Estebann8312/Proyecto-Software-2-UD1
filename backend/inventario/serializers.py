from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import (
    CategoriaPieza, Pieza, Proveedor, LoteCompra,
    Venta, DetalleVenta, Usuario, Cliente
)

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('password'):
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)


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

class DetalleVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleVenta
        fields = ['id_pieza', 'cantidad', 'precio_unitario']


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True, write_only=True)

    class Meta:
        model = Venta
        fields = ['id_venta', 'id_cliente', 'id_vendedor', 'fecha', 'metodo_pago', 'total', 'detalles']
        read_only_fields = ['total', 'fecha']

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')
        total = 0

        venta = Venta.objects.create(**validated_data, total=0)

        for detalle in detalles_data:
            pieza = detalle['id_pieza']
            cantidad = detalle['cantidad']

            if pieza.stock_actual < cantidad:
                venta.delete()
                raise serializers.ValidationError(
                    f"Stock insuficiente para la pieza '{pieza.nombre}'. Disponible: {pieza.stock_actual}"
                )

            DetalleVenta.objects.create(
                id_venta=venta,
                id_pieza=pieza,
                cantidad=cantidad,
                precio_unitario=detalle['precio_unitario']
            )

            pieza.stock_actual -= cantidad
            pieza.save()

            total += cantidad * detalle['precio_unitario']

        venta.total = total
        venta.save()
        return venta

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('password'):
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}  # para que nunca se devuelva en las respuestas
        }