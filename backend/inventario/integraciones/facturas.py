"""
Facturas de esta sede en el formato acordado entre sedes.

Es el mismo formato que publicó RepuAuto en su docs/API.md, campo por campo, para que
el consolidador trate igual a las dos sedes:

- Ventas: solo las activas (equivalen a sus "Completadas"); las anuladas no se envían.
- Compras: cada lote de compra es una factura de compra del proveedor.
- El IVA va incluido en el total: subtotal = total / (1 + IVA %) e iva = total - subtotal.
- Dinero como texto con 2 decimales; fechas ISO con la hora de Colombia (-05:00).
- Números: V-000123 para ventas y C-000045 para compras.
- Un cliente sin documento se reporta como consumidor final (222222222222, el código
  que usa la DIAN); un proveedor sin NIT, con documento null.
"""

from datetime import date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.utils import timezone

from ..models import LoteCompra, Venta

TIPOS = ("venta", "compra")
CENTAVO = Decimal("0.01")
CONSUMIDOR_FINAL = "222222222222"


class RangoInvalido(ValueError):
    pass


def config(clave):
    return settings.INTEGRACION[clave]


def leer_rango(desde_txt, hasta_txt):
    """?desde= y ?hasta= (AAAA-MM-DD). Por defecto, del primer día del mes actual a hoy."""
    hoy = timezone.localdate()
    try:
        hasta = date.fromisoformat(hasta_txt) if hasta_txt else hoy
        desde = date.fromisoformat(desde_txt) if desde_txt else hoy.replace(day=1)
    except ValueError:
        raise RangoInvalido("Las fechas deben tener el formato AAAA-MM-DD.")
    if desde > hasta:
        raise RangoInvalido("La fecha inicial no puede ser posterior a la final.")
    return desde, hasta


def texto(valor):
    """El dinero va como texto con 2 decimales, para no perder centavos."""
    return str(Decimal(valor).quantize(CENTAVO))


def separar_iva(total):
    """(subtotal, iva) de un total con el IVA incluido. Los dos suman el total exacto."""
    total = Decimal(total).quantize(CENTAVO)
    porcentaje = Decimal(str(config("IVA")))
    subtotal = (total / (1 + porcentaje / 100)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return subtotal, total - subtotal


def fecha_iso(valor):
    """Fecha y hora con la zona de Colombia, p. ej. 2026-10-30T10:15:00-05:00.
    Una fecha sin hora (los lotes) se toma a las 00:00."""
    if isinstance(valor, datetime):
        momento = timezone.localtime(valor)
    else:
        momento = timezone.make_aware(datetime.combine(valor, time.min))
    return momento.isoformat(timespec="seconds")


def _factura(tipo, numero, fecha, documento, nombre, total):
    subtotal, iva = separar_iva(total)
    return {
        "tipo": tipo,
        "numero": numero,
        "fecha": fecha_iso(fecha),
        "tercero": {"documento": documento, "nombre": nombre},
        "subtotal": texto(subtotal),
        "iva": texto(iva),
        "total": texto(total),
    }


def _factura_de_venta(venta):
    cliente = venta.id_cliente
    return _factura(
        "venta",
        f"V-{venta.id_venta:06d}",
        venta.fecha,
        (cliente.documento or "").strip() or CONSUMIDOR_FINAL,
        f"{cliente.nombres} {cliente.apellidos}".strip(),
        venta.total,
    )


def _factura_de_compra(lote):
    proveedor = lote.id_proveedor
    return _factura(
        "compra",
        f"C-{lote.id_lote:06d}",
        lote.fecha_compra,
        proveedor.nit or None,
        proveedor.nombre,
        lote.cantidad * lote.costo_unitario,
    )


def resumen(lista, tipo):
    del_tipo = [f for f in lista if f["tipo"] == tipo]

    def sumar(campo):
        return texto(sum((Decimal(f[campo]) for f in del_tipo), Decimal("0")))

    return {"cantidad": len(del_tipo), "subtotal": sumar("subtotal"), "iva": sumar("iva"), "total": sumar("total")}


def facturas(desde, hasta, tipo=None):
    """Facturas de venta y compra de esta sede entre dos fechas (incluidas)."""
    lista = []
    if tipo in (None, "venta"):
        ventas = (
            Venta.objects.filter(estado="activa", fecha__date__range=(desde, hasta))
            .select_related("id_cliente")
            .order_by("fecha", "id_venta")
        )
        lista += [_factura_de_venta(v) for v in ventas]
    if tipo in (None, "compra"):
        lotes = (
            LoteCompra.objects.filter(fecha_compra__range=(desde, hasta))
            .select_related("id_proveedor")
            .order_by("fecha_compra", "id_lote")
        )
        lista += [_factura_de_compra(l) for l in lotes]
    lista.sort(key=lambda f: (f["fecha"], f["numero"]))

    return {
        "sucursal": config("SUCURSAL"),
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "moneda": "COP",
        "iva_porcentaje": config("IVA"),
        "resumen": {t: resumen(lista, t) for t in TIPOS if tipo in (None, t)},
        "facturas": lista,
    }
