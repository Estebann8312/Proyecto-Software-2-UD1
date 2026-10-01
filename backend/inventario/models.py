from django.db import models


class Usuario(models.Model):
    ROL_CHOICES = [
        ('vendedor', 'Vendedor'),
        ('administrador', 'Administrador'),
    ]

    id_usuario = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    documento = models.CharField(max_length=30, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, unique=True, blank=True, null=True)
    rol = models.CharField(max_length=20, choices=ROL_CHOICES)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} ({self.rol})"


class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    documento = models.CharField(max_length=30, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, unique=True, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    fecha_registro = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


class CategoriaPieza(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        verbose_name_plural = "Categorías de pieza"

    def __str__(self):
        return self.nombre


class Pieza(models.Model):
    CONDICION_CHOICES = [
        ('nueva', 'Nueva'),
        ('reacondicionada', 'Reacondicionada'),
    ]

    id_pieza = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    id_categoria = models.ForeignKey(
        CategoriaPieza, on_delete=models.PROTECT, related_name='piezas'
    )
    condicion = models.CharField(max_length=20, choices=CONDICION_CHOICES)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    stock_actual = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = "Piezas"

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    contacto = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.nombre


class LoteCompra(models.Model):
    id_lote = models.AutoField(primary_key=True)
    id_proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name='lotes'
    )
    id_pieza = models.ForeignKey(
        Pieza, on_delete=models.PROTECT, related_name='lotes'
    )
    cantidad = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_compra = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Lote {self.id_lote} - {self.id_pieza.nombre}"


class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name='ventas'
    )
    id_vendedor = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name='ventas'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=30)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Venta {self.id_venta} - {self.id_cliente}"


class DetalleVenta(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    id_venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name='detalles'
    )
    id_pieza = models.ForeignKey(
        Pieza, on_delete=models.PROTECT, related_name='detalles_venta'
    )
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"Detalle {self.id_detalle} - Venta {self.id_venta_id}"