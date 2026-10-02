from django.contrib import admin

from .models import (
    Usuario, Cliente, CategoriaPieza, Pieza,
    Proveedor, LoteCompra, Venta, DetalleVenta
)

admin.site.register(Usuario)
admin.site.register(Cliente)
admin.site.register(CategoriaPieza)
admin.site.register(Pieza)
admin.site.register(Proveedor)
admin.site.register(LoteCompra)
admin.site.register(Venta)
admin.site.register(DetalleVenta)