"""
Cálculo de los informes del administrador (GET /api/reportes/).

Todo se calcula con agregaciones en la base de datos sobre un rango de fechas
(en la zona horaria de la tienda). Solo cuentan las ventas activas; las anuladas
se reportan aparte. Los valores de dinero están en pesos colombianos (COP).

El costo de lo vendido es una ESTIMACIÓN: no se guarda el costo de cada venta,
así que se usa el costo promedio ponderado de los lotes de cada pieza. Las piezas
sin lotes registrados no tienen costo conocido: su utilidad queda en None y no
entran al margen, para no inflarlo (se reportan aparte).
"""

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone

from .models import DetalleVenta, LoteCompra, Pieza, Venta

STOCK_BAJO = 3
DIAS_POR_DEFECTO = 30
DIAS_MAXIMOS = 366
TOP = 10

CERO = Decimal("0")
DINERO = DecimalField(max_digits=14, decimal_places=2)
SUBTOTAL = ExpressionWrapper(F("cantidad") * F("precio_unitario"), output_field=DINERO)


class RangoInvalido(ValueError):
    pass


def _dinero(valor):
    return str((valor or CERO).quantize(Decimal("0.01")))


def _porcentaje(parte, total):
    if not total:
        return None
    return round(float(parte) * 100 / float(total), 1)


def _variacion(actual, anterior):
    """Variación porcentual frente al periodo anterior; None si no hay base."""
    if not anterior:
        return None
    return round((float(actual) - float(anterior)) * 100 / float(anterior), 1)


def leer_rango(desde_txt, hasta_txt):
    """Interpreta ?desde= y ?hasta= (YYYY-MM-DD). Por defecto, los últimos 30 días."""
    hoy = timezone.localdate()
    try:
        hasta = date.fromisoformat(hasta_txt) if hasta_txt else hoy
        desde = date.fromisoformat(desde_txt) if desde_txt else hasta - timedelta(days=DIAS_POR_DEFECTO - 1)
    except ValueError:
        raise RangoInvalido("Las fechas deben tener el formato AAAA-MM-DD.")
    if desde > hasta:
        raise RangoInvalido("La fecha inicial no puede ser posterior a la final.")
    if (hasta - desde).days + 1 > DIAS_MAXIMOS:
        raise RangoInvalido(f"El rango no puede superar {DIAS_MAXIMOS} días.")
    return desde, hasta


def _costos_promedio():
    """Costo promedio ponderado por pieza según todos sus lotes: {id_pieza: Decimal}."""
    filas = LoteCompra.objects.values("id_pieza").annotate(
        unidades=Sum("cantidad"),
        monto=Sum(ExpressionWrapper(F("cantidad") * F("costo_unitario"), output_field=DINERO)),
    )
    return {f["id_pieza"]: f["monto"] / f["unidades"] for f in filas if f["unidades"]}


def _resumen_ventas(ventas):
    datos = ventas.aggregate(
        ingresos=Coalesce(Sum("total"), CERO, output_field=DINERO),
        cantidad=Count("id_venta"),
        clientes=Count("id_cliente", distinct=True),
    )
    return datos


def generar_reporte(desde, hasta):
    dias = (hasta - desde).days + 1
    costos = _costos_promedio()

    ventas_rango = Venta.objects.filter(fecha__date__range=(desde, hasta))
    activas = ventas_rango.filter(estado="activa")
    anuladas = ventas_rango.filter(estado="anulada")
    detalles = DetalleVenta.objects.filter(id_venta__in=activas)

    # --- Resumen y comparación con el periodo anterior de igual duración -------
    actual = _resumen_ventas(activas)
    anterior_hasta = desde - timedelta(days=1)
    anterior_desde = anterior_hasta - timedelta(days=dias - 1)
    anterior = _resumen_ventas(
        Venta.objects.filter(estado="activa", fecha__date__range=(anterior_desde, anterior_hasta))
    )
    anuladas_datos = anuladas.aggregate(
        cantidad=Count("id_venta"),
        monto=Coalesce(Sum("total"), CERO, output_field=DINERO),
    )

    # --- Por pieza: base para unidades, costo estimado, categorías y ranking ---
    por_pieza = list(
        detalles.values(
            "id_pieza",
            "id_pieza__nombre",
            "id_pieza__condicion",
            "id_pieza__id_categoria__nombre",
        ).annotate(unidades=Sum("cantidad"), ingresos=Sum(SUBTOTAL))
    )
    unidades_vendidas = 0
    costo_estimado = CERO
    ingresos_con_costo = CERO
    piezas_sin_costo = 0
    por_categoria = {}
    for fila in por_pieza:
        costo_unit = costos.get(fila["id_pieza"])
        fila["costo"] = None if costo_unit is None else costo_unit * fila["unidades"]
        unidades_vendidas += fila["unidades"]
        cat = por_categoria.setdefault(
            fila["id_pieza__id_categoria__nombre"],
            {"unidades": 0, "ingresos": CERO, "ingresos_con_costo": CERO, "costo": CERO},
        )
        cat["unidades"] += fila["unidades"]
        cat["ingresos"] += fila["ingresos"]
        if fila["costo"] is None:
            piezas_sin_costo += 1
            continue
        costo_estimado += fila["costo"]
        ingresos_con_costo += fila["ingresos"]
        cat["ingresos_con_costo"] += fila["ingresos"]
        cat["costo"] += fila["costo"]

    ingresos = actual["ingresos"]
    utilidad = ingresos_con_costo - costo_estimado

    # --- Serie diaria (todos los días del rango, también los que no tuvieron ventas)
    diarias = {
        f["dia"]: f
        for f in activas.annotate(dia=TruncDate("fecha"))
        .values("dia")
        .annotate(ingresos=Sum("total"), ventas=Count("id_venta"))
    }
    por_dia = []
    for i in range(dias):
        d = desde + timedelta(days=i)
        f = diarias.get(d)
        por_dia.append({
            "fecha": d.isoformat(),
            "ventas": f["ventas"] if f else 0,
            "ingresos": _dinero(f["ingresos"] if f else CERO),
        })

    # --- Métodos de pago ------------------------------------------------------
    por_metodo = [
        {
            "metodo": f["metodo_pago"],
            "ventas": f["ventas"],
            "ingresos": _dinero(f["ingresos"]),
            "porcentaje": _porcentaje(f["ingresos"], ingresos),
        }
        for f in activas.values("metodo_pago")
        .annotate(ventas=Count("id_venta"), ingresos=Sum("total"))
        .order_by("-ingresos")
    ]

    # --- Vendedores -------------------------------------------------------------
    por_vendedor = [
        {
            "id_usuario": f["id_vendedor"],
            "nombre": f"{f['id_vendedor__nombres']} {f['id_vendedor__apellidos']}",
            "rol": f["id_vendedor__rol"],
            "ventas": f["ventas"],
            "ingresos": _dinero(f["ingresos"]),
            "ticket_promedio": _dinero(f["ingresos"] / f["ventas"]),
            "porcentaje": _porcentaje(f["ingresos"], ingresos),
        }
        for f in activas.values(
            "id_vendedor", "id_vendedor__nombres", "id_vendedor__apellidos", "id_vendedor__rol"
        )
        .annotate(ventas=Count("id_venta"), ingresos=Sum("total"))
        .order_by("-ingresos")
    ]

    # --- Clientes que más compraron ------------------------------------------
    top_clientes = [
        {
            "id_cliente": f["id_cliente"],
            "nombre": f"{f['id_cliente__nombres']} {f['id_cliente__apellidos']}",
            "con_cuenta": f["id_cliente__user"] is not None,
            "compras": f["compras"],
            "ingresos": _dinero(f["ingresos"]),
            "ultima_compra": timezone.localtime(f["ultima"]).isoformat(),
        }
        for f in activas.values(
            "id_cliente", "id_cliente__nombres", "id_cliente__apellidos", "id_cliente__user"
        )
        .annotate(compras=Count("id_venta"), ingresos=Sum("total"), ultima=Max("fecha"))
        .order_by("-ingresos")[:TOP]
    ]

    # --- Piezas más vendidas (por ingresos) ----------------------------------
    por_pieza.sort(key=lambda f: (f["ingresos"], f["unidades"]), reverse=True)
    top_piezas = [
        {
            "id_pieza": f["id_pieza"],
            "nombre": f["id_pieza__nombre"],
            "categoria": f["id_pieza__id_categoria__nombre"],
            "condicion": f["id_pieza__condicion"],
            "unidades": f["unidades"],
            "ingresos": _dinero(f["ingresos"]),
            "utilidad_estimada": None if f["costo"] is None else _dinero(f["ingresos"] - f["costo"]),
            "margen": None if f["costo"] is None else _porcentaje(f["ingresos"] - f["costo"], f["ingresos"]),
        }
        for f in por_pieza[:TOP]
    ]

    categorias = sorted(
        (
            {
                "categoria": nombre,
                "unidades": c["unidades"],
                "ingresos": _dinero(c["ingresos"]),
                "utilidad_estimada": _dinero(c["ingresos_con_costo"] - c["costo"]),
                "margen": _porcentaje(c["ingresos_con_costo"] - c["costo"], c["ingresos_con_costo"]),
                "porcentaje": _porcentaje(c["ingresos"], ingresos),
            }
            for nombre, c in por_categoria.items()
        ),
        key=lambda c: Decimal(c["ingresos"]),
        reverse=True,
    )

    # --- Compras a proveedores en el rango -----------------------------------
    lotes = LoteCompra.objects.filter(fecha_compra__range=(desde, hasta))
    costo_lote = ExpressionWrapper(F("cantidad") * F("costo_unitario"), output_field=DINERO)
    compras_proveedor = [
        {
            "id_proveedor": f["id_proveedor"],
            "proveedor": f["id_proveedor__nombre"],
            "lotes": f["lotes"],
            "unidades": f["unidades"],
            "monto": _dinero(f["monto"]),
        }
        for f in lotes.values("id_proveedor", "id_proveedor__nombre")
        .annotate(lotes=Count("id_lote"), unidades=Sum("cantidad"), monto=Sum(costo_lote))
        .order_by("-monto")
    ]
    compras_total = lotes.aggregate(
        lotes=Count("id_lote"),
        unidades=Coalesce(Sum("cantidad"), 0),
        monto=Coalesce(Sum(costo_lote), CERO, output_field=DINERO),
    )

    # --- Inventario (foto actual, no depende del rango) ----------------------
    piezas = list(
        Pieza.objects.select_related("id_categoria").annotate(
            vendidas_rango=Coalesce(
                Sum(
                    "detalles_venta__cantidad",
                    filter=Q(detalles_venta__id_venta__in=activas),
                ),
                0,
            )
        )
    )
    valor_costo = CERO
    valor_venta = CERO
    valor_venta_con_costo = CERO
    sin_costo_inventario = 0
    unidades_stock = 0
    criticas = []
    sin_movimiento = []
    for p in piezas:
        unidades_stock += p.stock_actual
        valor_venta += p.precio_venta * p.stock_actual
        if p.id_pieza in costos:
            valor_costo += costos[p.id_pieza] * p.stock_actual
            valor_venta_con_costo += p.precio_venta * p.stock_actual
        elif p.stock_actual > 0:
            sin_costo_inventario += 1
        if p.stock_actual <= STOCK_BAJO:
            criticas.append(p)
        if p.stock_actual > 0 and p.vendidas_rango == 0:
            sin_movimiento.append(p)

    def _pieza_inventario(p):
        return {
            "id_pieza": p.id_pieza,
            "nombre": p.nombre,
            "categoria": p.id_categoria.nombre,
            "condicion": p.condicion,
            "stock": p.stock_actual,
            "precio_venta": _dinero(p.precio_venta),
            "valor_venta": _dinero(p.precio_venta * p.stock_actual),
        }

    criticas.sort(key=lambda p: (p.stock_actual, p.nombre))
    sin_movimiento.sort(key=lambda p: p.precio_venta * p.stock_actual, reverse=True)

    return {
        "rango": {
            "desde": desde.isoformat(),
            "hasta": hasta.isoformat(),
            "dias": dias,
            "anterior_desde": anterior_desde.isoformat(),
            "anterior_hasta": anterior_hasta.isoformat(),
        },
        "generado": timezone.localtime().isoformat(),
        "moneda": "COP",
        "resumen": {
            "ingresos": _dinero(ingresos),
            "ventas": actual["cantidad"],
            "ticket_promedio": _dinero(ingresos / actual["cantidad"] if actual["cantidad"] else CERO),
            "unidades_vendidas": unidades_vendidas,
            "clientes_distintos": actual["clientes"],
            "costo_estimado": _dinero(costo_estimado),
            "utilidad_estimada": _dinero(utilidad),
            "margen": _porcentaje(utilidad, ingresos_con_costo),
            "piezas_sin_costo": piezas_sin_costo,
            "ingresos_sin_costo": _dinero(ingresos - ingresos_con_costo),
            "anuladas": anuladas_datos["cantidad"],
            "monto_anulado": _dinero(anuladas_datos["monto"]),
            "ingresos_anterior": _dinero(anterior["ingresos"]),
            "ventas_anterior": anterior["cantidad"],
            "variacion_ingresos": _variacion(ingresos, anterior["ingresos"]),
            "variacion_ventas": _variacion(actual["cantidad"], anterior["cantidad"]),
        },
        "por_dia": por_dia,
        "por_metodo_pago": por_metodo,
        "por_categoria": categorias,
        "por_vendedor": por_vendedor,
        "top_piezas": top_piezas,
        "top_clientes": top_clientes,
        "compras": {
            "lotes": compras_total["lotes"],
            "unidades": compras_total["unidades"],
            "monto": _dinero(compras_total["monto"]),
            "por_proveedor": compras_proveedor,
        },
        "inventario": {
            "referencias": len(piezas),
            "unidades": unidades_stock,
            "valor_costo": _dinero(valor_costo),
            "valor_venta": _dinero(valor_venta),
            "utilidad_potencial": _dinero(valor_venta_con_costo - valor_costo),
            "piezas_sin_costo": sin_costo_inventario,
            "agotadas": sum(1 for p in piezas if p.stock_actual <= 0),
            "stock_bajo": sum(1 for p in piezas if 0 < p.stock_actual <= STOCK_BAJO),
            "umbral_stock_bajo": STOCK_BAJO,
            "criticas": [_pieza_inventario(p) for p in criticas],
            "sin_movimiento": [_pieza_inventario(p) for p in sin_movimiento],
        },
    }
