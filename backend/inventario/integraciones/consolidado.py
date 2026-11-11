"""
Consolidado entre sedes: junta nuestras facturas con las de RepuAuto.

Nuestra sede se calcula directamente (sin pasar por HTTP). Si RepuAuto no responde,
el consolidado sale igual con nuestra sede y marca la otra con su error: nunca se cae
la pantalla por culpa de la otra sede.
"""

from decimal import Decimal, InvalidOperation

from . import facturas as propias
from . import inventario as inventario_propio
from . import repuauto

CAMPOS = ("subtotal", "iva", "total")


def _decimal(valor):
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def _valida(factura):
    """Una factura de la otra sede se usa solo si su tipo y sus montos son legibles."""
    if not isinstance(factura, dict) or factura.get("tipo") not in propias.TIPOS:
        return False
    try:
        return all(Decimal(str(factura.get(c))).is_finite() for c in CAMPOS)
    except InvalidOperation:
        return False


def _resumen_de(lista):
    return {t: propias.resumen(lista, t) for t in propias.TIPOS}


def _sede(datos, estado="ok", error=None, propia=False):
    facturas = []
    if datos:
        for f in datos["facturas"]:
            if _valida(f):
                facturas.append({**f, "sucursal": datos.get("sucursal") or "Sin nombre"})
    return {
        "sucursal": (datos or {}).get("sucursal"),
        "propia": propia,
        "estado": estado,
        "error": error,
        "iva_porcentaje": (datos or {}).get("iva_porcentaje"),
        # El resumen se recalcula de las facturas: no se confía en el que mande la otra sede.
        "resumen": _resumen_de(facturas),
        "facturas": facturas,
    }


def consolidar(desde, hasta):
    sedes = [_sede(propias.facturas(desde, hasta), propia=True)]

    if not repuauto.configurado():
        aliada = _sede(None, estado="sin_configurar",
                       error="Falta configurar REPUAUTO_URL, REPUAUTO_CORREO y REPUAUTO_CLAVE en el .env.")
    else:
        try:
            aliada = _sede(repuauto.facturas(desde, hasta))
        except repuauto.AliadoNoDisponible as e:
            aliada = _sede(None, estado="error", error=str(e))
    aliada["sucursal"] = aliada["sucursal"] or "RepuAuto"
    sedes.append(aliada)

    todas = sorted(
        (f for s in sedes for f in s["facturas"]),
        key=lambda f: (str(f.get("fecha", "")), f["sucursal"], str(f.get("numero", ""))),
    )
    total = {}
    for tipo in propias.TIPOS:
        del_tipo = [f for f in todas if f["tipo"] == tipo]
        total[tipo] = {"cantidad": len(del_tipo)}
        for campo in CAMPOS:
            total[tipo][campo] = propias.texto(sum((_decimal(f.get(campo)) for f in del_tipo), Decimal("0")))

    # Las facturas ya van dentro de "facturas"; en cada sede solo queda su resumen.
    for s in sedes:
        del s["facturas"]

    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "moneda": "COP",
        "sedes": sedes,
        "total": total,
        "facturas": todas,
    }


# ---------------------------------------------------------------------------
# Inventario
# ---------------------------------------------------------------------------

def _producto_valido(producto):
    """Un producto de la otra sede se usa solo si sus datos básicos son legibles."""
    if not isinstance(producto, dict) or not isinstance(producto.get("nombre"), str):
        return False
    if producto.get("estado") not in inventario_propio.ESTADOS:
        return False
    stock = producto.get("stock")
    if not isinstance(stock, int) or isinstance(stock, bool) or stock < 0:
        return False
    try:
        return all(Decimal(str(producto.get(c))).is_finite() for c in ("precio_venta", "valor"))
    except InvalidOperation:
        return False


def _sede_inventario(datos, estado="ok", error=None, propia=False):
    productos = []
    if datos:
        nombre = datos.get("sucursal") or "Sin nombre"
        productos = [{**p, "sucursal": nombre} for p in datos["productos"] if _producto_valido(p)]
    return {
        "sucursal": (datos or {}).get("sucursal"),
        "propia": propia,
        "estado": estado,
        "error": error,
        "fecha": (datos or {}).get("fecha"),
        # Se recalcula de los productos: no se confía en el resumen de la otra sede.
        "resumen": inventario_propio.resumen(productos),
        "productos": productos,
    }


def consolidar_inventario():
    sedes = [_sede_inventario(inventario_propio.inventario(), propia=True)]

    if not repuauto.configurado():
        aliada = _sede_inventario(None, estado="sin_configurar",
                                  error="Falta configurar REPUAUTO_URL, REPUAUTO_CORREO y REPUAUTO_CLAVE en el .env.")
    else:
        try:
            aliada = _sede_inventario(repuauto.inventario())
        except repuauto.AliadoNoDisponible as e:
            aliada = _sede_inventario(None, estado="error", error=str(e))
    aliada["sucursal"] = aliada["sucursal"] or "RepuAuto"
    sedes.append(aliada)

    productos = [p for s in sedes for p in s["productos"]]
    for s in sedes:
        del s["productos"]
    return {
        "moneda": "COP",
        "sedes": sedes,
        "total": inventario_propio.resumen(productos),
        "productos": productos,
    }
