from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from decimal import Decimal
from django.db import transaction
from django.db.models import F

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

    def create(self, validated_data):
        with transaction.atomic():
            lote = super().create(validated_data)
            Pieza.objects.filter(pk=lote.id_pieza_id).update(
                stock_actual=F('stock_actual') + lote.cantidad
            )
        return lote

class DetalleVentaSerializer(serializers.ModelSerializer):
    pieza_nombre = serializers.CharField(source='id_pieza.nombre', read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = DetalleVenta
        fields = ['id_pieza', 'pieza_nombre', 'cantidad', 'precio_unitario', 'subtotal']
        read_only_fields = ['precio_unitario']

    def get_subtotal(self, obj):
        return obj.cantidad * obj.precio_unitario


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True)

    class Meta:
        model = Venta
        fields = ['id_venta', 'id_cliente', 'id_vendedor', 'fecha',
                  'metodo_pago', 'total', 'detalles']
        read_only_fields = ['total', 'fecha']

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError("La venta debe tener al menos una pieza.")
        ids = [d['id_pieza'].pk for d in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Una misma pieza no puede repetirse; suma las cantidades en una sola línea."
            )
        return value

    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles')

        with transaction.atomic():
            ids = [d['id_pieza'].pk for d in detalles_data]
            piezas = {
                p.pk: p
                for p in Pieza.objects.select_for_update().filter(pk__in=ids).order_by('pk')
            }

            venta = Venta.objects.create(total=0, **validated_data)
            total = Decimal('0')

            for d in detalles_data:
                pieza = piezas[d['id_pieza'].pk]
                cantidad = d['cantidad']

                if pieza.stock_actual < cantidad:
                    raise serializers.ValidationError({
                        'detalles': f"Stock insuficiente para '{pieza.nombre}'. "
                                    f"Disponible: {pieza.stock_actual}, solicitado: {cantidad}."
                    })

                DetalleVenta.objects.create(
                    id_venta=venta,
                    id_pieza=pieza,
                    cantidad=cantidad,
                    precio_unitario=pieza.precio_venta,
                )
                pieza.stock_actual -= cantidad
                pieza.save(update_fields=['stock_actual'])
                total += pieza.precio_venta * cantidad

            venta.total = total
            venta.save(update_fields=['total'])

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