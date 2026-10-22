from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import F
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

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
from .permissions import get_empleado

User = get_user_model()


# ---------------------------------------------------------------------------
# Utilidades de validación compartidas
# ---------------------------------------------------------------------------

def normalizar_email(value):
    return value.strip().lower()


def email_en_uso(email, excluir_user=None, excluir_cliente=None, excluir_usuario=None):
    """True si el email ya existe en User, Cliente o Usuario (sin distinguir mayúsculas)."""
    users = User.objects.filter(email__iexact=email)
    clientes = Cliente.objects.filter(email__iexact=email)
    empleados = Usuario.objects.filter(email__iexact=email)
    if excluir_user is not None:
        users = users.exclude(pk=excluir_user.pk)
    if excluir_cliente is not None:
        clientes = clientes.exclude(pk=excluir_cliente.pk)
    if excluir_usuario is not None:
        empleados = empleados.exclude(pk=excluir_usuario.pk)
    return users.exists() or clientes.exists() or empleados.exists()


def validar_password(password, user=None):
    """Aplica AUTH_PASSWORD_VALIDATORS de settings y devuelve errores de DRF."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as e:
        raise serializers.ValidationError(list(e.messages))
    return password


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------

class TokenConRolSerializer(TokenObtainPairSerializer):
    """Login JWT que además incluye el rol en el token y en la respuesta."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        empleado = get_empleado(user)
        token["rol"] = empleado.rol if empleado else "cliente"
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        empleado = get_empleado(self.user)
        data["rol"] = empleado.rol if empleado else "cliente"
        return data


class RegisterSerializer(serializers.Serializer):
    """Registro público: SIEMPRE crea un cliente, nunca un empleado."""

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    documento = serializers.CharField(max_length=30, required=False, allow_blank=True)
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ese nombre de usuario ya existe.")
        return value

    def validate_email(self, value):
        value = normalizar_email(value)
        if email_en_uso(value):
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return value

    def validate(self, attrs):
        usuario_tmp = User(
            username=attrs.get("username"),
            email=attrs.get("email"),
            first_name=attrs.get("first_name"),
            last_name=attrs.get("last_name"),
        )
        try:
            validar_password(attrs["password"], user=usuario_tmp)
        except serializers.ValidationError as e:
            raise serializers.ValidationError({"password": e.detail})
        return attrs

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



# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------

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

    @transaction.atomic
    def create(self, validated_data):
        lote = super().create(validated_data)
        Pieza.objects.filter(pk=lote.id_pieza_id).update(
            stock_actual=F("stock_actual") + lote.cantidad
        )
        return lote


class PiezaSerializer(serializers.ModelSerializer):
    """Vista completa para empleados (incluye stock real y lotes con costos)."""

    lotes = LoteCompraSerializer(many=True, read_only=True)

    class Meta:
        model = Pieza
        fields = "__all__"
        # El stock solo cambia por lotes (entradas) y ventas/anulaciones (salidas),
        # así siempre cuadra con el historial.
        read_only_fields = ["stock_actual"]


class PiezaPublicSerializer(serializers.ModelSerializer):
    """Catálogo público: sin stock exacto ni costos de proveedor."""

    categoria_nombre = serializers.CharField(source="id_categoria.nombre", read_only=True)
    en_stock = serializers.SerializerMethodField()

    class Meta:
        model = Pieza
        fields = [
            "id_pieza",
            "nombre",
            "categoria_nombre",
            "condicion",
            "precio_venta",
            "descripcion",
            "en_stock",
        ]

    def get_en_stock(self, obj):
        return obj.stock_actual > 0


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------

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
            "estado",
            "detalles",
        ]
        # id_vendedor lo asigna la vista con el empleado autenticado.
        read_only_fields = ["id_vendedor", "total", "fecha", "estado"]

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
            # Bloqueo ordenado por PK para evitar interbloqueos entre ventas simultáneas.
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



# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

class UsuarioSerializer(serializers.ModelSerializer):
    """
    Gestión de empleados (solo administrador).
    Crear un empleado crea también su cuenta de acceso (User) en una sola transacción.
    """

    username = serializers.CharField(source="user.username", max_length=150)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = [
            "id_usuario",
            "username",
            "password",
            "nombres",
            "apellidos",
            "documento",
            "telefono",
            "email",
            "rol",
            "fecha_registro",
        ]
        read_only_fields = ["fecha_registro"]

    def validate_email(self, value):
        value = normalizar_email(value)
        instancia = self.instance
        if email_en_uso(
            value,
            excluir_user=instancia.user if instancia else None,
            excluir_usuario=instancia,
        ):
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return value

    def validate_username(self, value):
        value = value.strip()
        qs = User.objects.filter(username__iexact=value)
        if self.instance and self.instance.user:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise serializers.ValidationError("Ese nombre de usuario ya existe.")
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "La contraseña es obligatoria."})
        if attrs.get("password"):
            try:
                validar_password(attrs["password"])
            except serializers.ValidationError as e:
                raise serializers.ValidationError({"password": e.detail})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user_data = validated_data.pop("user")
        password = validated_data.pop("password")
        user = User.objects.create_user(
            username=user_data["username"],
            email=validated_data["email"],
            password=password,
            first_name=validated_data["nombres"][:150],
            last_name=validated_data["apellidos"][:150],
        )
        return Usuario.objects.create(user=user, **validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)

        user = instance.user
        if user is not None:
            if "username" in user_data:
                user.username = user_data["username"]
            user.email = instance.email
            user.first_name = instance.nombres[:150]
            user.last_name = instance.apellidos[:150]
            if password:
                user.set_password(password)
            user.save()
        return instance


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"
        read_only_fields = ["user"]

    def validate_email(self, value):
        if not value:
            return None
        value = normalizar_email(value)
        instancia = self.instance
        if email_en_uso(
            value,
            excluir_user=instancia.user if instancia else None,
            excluir_cliente=instancia,
        ):
            raise serializers.ValidationError("Ese correo ya está registrado.")
        return value