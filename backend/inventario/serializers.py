from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from decimal import Decimal
from django.db import transaction
from django.db.models import F
from django.db import transaction
from rest_framework import serializers


from .models import (
    Usuario,
    CategoriaPieza,
    Pieza,
    Proveedor,
    LoteCompra,
    Venta,
    DetalleVenta,
    Cliente,
)

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    documento = serializers.CharField(max_length=30, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya existe.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ese correo ya está registrado.")
        if Cliente.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ese correo ya está registrado como cliente.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        documento = validated_data.pop("documento", "")
        telefono = validated_data.pop("telefono", "")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )

        Cliente.objects.create(
            user=user,
            nombres=validated_data["first_name"],
            apellidos=validated_data["last_name"],
            documento=documento or None,
            telefono=telefono or None,
            email=validated_data["email"],
        )

        return user


class CategoriaPiezaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaPieza
        fields = "__all__"


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"


class LoteCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoteCompra
        fields = "__all__"

    def create(self, validated_data):
        with transaction.atomic():
            lote = super().create(validated_data)
            Pieza.objects.filter(pk=lote.id_pieza_id).update(
                stock_actual=F("stock_actual") + lote.cantidad
            )
        return lote

class PiezaSerializer(serializers.ModelSerializer):
    lotes = LoteCompraSerializer(many=True, read_only=True)
    class Meta:
        model = Pieza
        fields = "__all__"


class DetalleVentaSerializer(serializers.ModelSerializer):
    pieza_nombre = serializers.CharField(source="id_pieza.nombre", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = DetalleVenta
        fields = ["id_pieza", "pieza_nombre", "cantidad", "precio_unitario", "subtotal"]
        read_only_fields = ["precio_unitario"]

    def get_subtotal(self, obj):
        return obj.cantidad * obj.precio_unitario


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True)

    class Meta:
        model = Venta
        fields = [
            "id_venta",
            "id_cliente",
            "id_vendedor",
            "fecha",
            "metodo_pago",
            "total",
            "detalles",
        ]
        read_only_fields = ["total", "fecha"]

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError("La venta debe tener al menos una pieza.")
        ids = [d["id_pieza"].pk for d in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError(
                "Una misma pieza no puede repetirse; suma las cantidades en una sola línea."
            )
        return value

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles")

        with transaction.atomic():
            ids = [d["id_pieza"].pk for d in detalles_data]
            piezas = {
                p.pk: p
                for p in Pieza.objects.select_for_update().filter(pk__in=ids).order_by("pk")
            }

            venta = Venta.objects.create(total=0, **validated_data)
            total = Decimal("0")

            for d in detalles_data:
                pieza = piezas[d["id_pieza"].pk]
                cantidad = d["cantidad"]

                if pieza.stock_actual < cantidad:
                    raise serializers.ValidationError({
                        "detalles": f"Stock insuficiente para '{pieza.nombre}'. "
                                    f"Disponible: {pieza.stock_actual}, solicitado: {cantidad}."
                    })

                DetalleVenta.objects.create(
                    id_venta=venta,
                    id_pieza=pieza,
                    cantidad=cantidad,
                    precio_unitario=pieza.precio_venta,
                )
                pieza.stock_actual -= cantidad
                pieza.save(update_fields=["stock_actual"])
                total += pieza.precio_venta * cantidad

            venta.total = total
            venta.save(update_fields=["total"])

        return venta


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = "__all__"
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        validated_data["password"] = make_password(validated_data["password"])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("password"):
            validated_data["password"] = make_password(validated_data["password"])
        return super().update(instance, validated_data)


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"
        read_only_fields = ["user"]

class PiezaPublicSerializer(serializers.ModelSerializer):
    # Opcional: Mostrar el nombre de la categoría en lugar del ID
    categoria_nombre = serializers.CharField(source='id_categoria.nombre', read_only=True)
    
    # En lugar de mostrar 'stock_actual', mostraremos un booleano (True/False)
    en_stock = serializers.SerializerMethodField()

    class Meta:
        model = Pieza
        # AQUI DEFINIMOS SOLO LO QUE QUEREMOS QUE VEA EL PÚBLICO:
        fields = [
            'id_pieza', 
            'nombre', 
            'categoria_nombre', 
            'condicion', 
            'precio_venta', 
            'descripcion', 
            'en_stock'
        ]

    def get_en_stock(self, obj):
        # Retorna True si hay más de 0, False si está agotado. Oculta el número real.
        return obj.stock_actual > 0