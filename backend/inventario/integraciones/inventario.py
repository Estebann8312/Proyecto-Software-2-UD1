"""
Inventario de esta sede en el formato acordado entre sedes (GET /api/inventario).

Es el formato que publicó RepuAuto en la sección 3 de su docs/API.md, campo por campo:

- estado: "agotado" si el stock es 0, "stock_bajo" si es menor que el mínimo y
  "en_stock" en los demás casos.
- valor: stock × precio de venta (con IVA incluido), como texto con 2 decimales.
- resumen: siempre de todo el inventario, aunque se filtre por estado.
- orden: por categoría y nombre.

Diferencias con RepuAuto y cómo se resuelven:
- PC Stock no maneja código de producto: se arma con el id (PZ-000012).
- PC Stock no maneja un mínimo por pieza: marca "stock bajo" con 3 unidades o menos
  (el mismo criterio de sus pantallas y reportes). Con la regla de RepuAuto
  ("menor que el mínimo"), eso equivale a un mínimo de 4 para todas las piezas.
- Una pieza sin marca registrada sale con "Sin marca".
"""

from decimal import Decimal

from django.utils import timezone

from ..models import Pieza
from ..reportes import STOCK_BAJO
from .facturas import config, fecha_iso, texto

ESTADOS = ("en_stock", "stock_bajo", "agotado")
STOCK_MINIMO = STOCK_BAJO + 1


class EstadoInvalido(ValueError):
    pass


def leer_estado(valor):
    valor = (valor or "").strip().lower() or None
    if valor is not None and valor not in ESTADOS:
        raise EstadoInvalido(
            'El estado debe ser "en_stock", "stock_bajo" o "agotado", o no enviarlo para traer todos.'
        )
    return valor


def estado_de_stock(stock, minimo=STOCK_MINIMO):
    if stock == 0:
        return "agotado"
    if stock < minimo:
        return "stock_bajo"
    return "en_stock"


def codigo(pieza):
    return f"PZ-{pieza.id_pieza:06d}"


def _producto(pieza):
    return {
        "codigo": codigo(pieza),
        "nombre": pieza.nombre,
        "categoria": pieza.id_categoria.nombre,
        "marca": (pieza.marca or "").strip() or "Sin marca",
        "stock": pieza.stock_actual,
        "stock_minimo": STOCK_MINIMO,
        "precio_venta": texto(pieza.precio_venta),
        "valor": texto(pieza.precio_venta * pieza.stock_actual),
        "estado": estado_de_stock(pieza.stock_actual),
    }


def resumen(productos):
    return {
        "productos": len(productos),
        "unidades": sum(p["stock"] for p in productos),
        "valor": texto(sum((Decimal(p["valor"]) for p in productos), Decimal("0"))),
        **{e: sum(1 for p in productos if p["estado"] == e) for e in ESTADOS},
    }


def inventario(estado=None):
    """Piezas de esta sede con su stock de hoy. estado filtra la lista, no el resumen."""
    piezas = Pieza.objects.select_related("id_categoria").order_by("id_categoria__nombre", "nombre")
    productos = [_producto(p) for p in piezas]
    return {
        "sucursal": config("SUCURSAL"),
        "fecha": fecha_iso(timezone.now()),
        "moneda": "COP",
        "resumen": resumen(productos),
        "productos": [p for p in productos if estado in (None, p["estado"])],
    }
