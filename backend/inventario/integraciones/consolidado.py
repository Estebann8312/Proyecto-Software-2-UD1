"""
Consolidado entre sedes: junta nuestras facturas con las de RepuAuto.

Nuestra sede se calcula directamente (sin pasar por HTTP). Si RepuAuto no responde,
el consolidado sale igual con nuestra sede y marca la otra con su error: nunca se cae
la pantalla por culpa de la otra sede.
"""

from decimal import Decimal, InvalidOperation

from . import facturas as propias
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
