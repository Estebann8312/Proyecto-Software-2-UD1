"""
Simulador de la API de RepuAuto, para probar la integración sin depender de ellos.

Responde POST /api/login y GET /api/facturas con el mismo formato de su docs/API.md
(https://github.com/Thiago3108/repuauto/blob/main/docs/API.md), con facturas inventadas
dentro del rango que se pida. Solo usa la biblioteca estándar de Python.

Uso (desde backend/):
    uv run python simular_repuauto.py            # escucha en http://127.0.0.1:5000

Y en backend/.env:
    REPUAUTO_URL=http://127.0.0.1:5000/api
    REPUAUTO_CORREO=integracion@repuauto.com
    REPUAUTO_CLAVE=simulador
"""

import json
import random
import sys
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
CORREO, CLAVE, TOKEN = "integracion@repuauto.com", "simulador", "token-del-simulador"
IVA = Decimal("19")
CENTAVO = Decimal("0.01")

CLIENTES = [
    ("1098000001", "Carlos Andrés Rueda Pinzón"),
    ("1095123456", "Luisa Fernanda Ardila Mantilla"),
    ("91234567", "Jorge Enrique Barajas Díaz"),
    ("1102345678", "Natalia Gómez Serrano"),
]
PROVEEDORES = [
    ("900123456-7", "Autopartes del Oriente S.A.S."),
    ("901765432-1", "Lubricantes y Filtros Santander Ltda."),
]


def separar_iva(total):
    subtotal = (total / (1 + IVA / 100)).quantize(CENTAVO, rounding=ROUND_HALF_UP)
    return subtotal, total - subtotal


def factura(tipo, numero, momento, tercero, total):
    subtotal, iva = separar_iva(total)
    return {
        "tipo": tipo,
        "numero": numero,
        "fecha": momento.strftime("%Y-%m-%dT%H:%M:%S-05:00"),
        "tercero": {"documento": tercero[0], "nombre": tercero[1]},
        "subtotal": str(subtotal),
        "iva": str(iva),
        "total": str(total.quantize(CENTAVO)),
    }


def facturas(desde, hasta, tipo):
    """Facturas inventadas pero estables: el mismo rango siempre da lo mismo."""
    lista = []
    dia = desde
    while dia <= hasta:
        azar = random.Random(dia.toordinal())
        for i in range(azar.choice([0, 1, 1, 2])):
            momento = datetime.combine(dia, datetime.min.time()) + timedelta(hours=9 + 3 * i, minutes=azar.randint(0, 59))
            total = Decimal(azar.randrange(45, 900) * 1000)
            lista.append(factura("venta", f"V-{dia.toordinal() % 100000:05d}{i}", momento, azar.choice(CLIENTES), total))
        if dia.weekday() == 0:  # una compra a proveedor cada lunes
            momento = datetime.combine(dia, datetime.min.time()) + timedelta(hours=8, minutes=30)
            total = Decimal(azar.randrange(800, 4000) * 1000)
            lista.append(factura("compra", f"C-{dia.toordinal() % 1000000:06d}", momento, azar.choice(PROVEEDORES), total))
        dia += timedelta(days=1)
    if tipo:
        lista = [f for f in lista if f["tipo"] == tipo]
    lista.sort(key=lambda f: (f["fecha"], f["numero"]))

    def resumen(t):
        del_tipo = [f for f in lista if f["tipo"] == t]
        suma = lambda c: str(sum((Decimal(f[c]) for f in del_tipo), Decimal("0")).quantize(CENTAVO))  # noqa: E731
        return {"cantidad": len(del_tipo), "subtotal": suma("subtotal"), "iva": suma("iva"), "total": suma("total")}

    return {
        "sucursal": "Bucaramanga",
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "moneda": "COP",
        "iva_porcentaje": 19,
        "resumen": {t: resumen(t) for t in ("venta", "compra") if tipo in (None, t)},
        "facturas": lista,
    }


class Manejador(BaseHTTPRequestHandler):
    def responder(self, codigo, datos):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") != "/api/login":
            return self.responder(404, {"error": "La ruta no existe."})
        try:
            datos = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except ValueError:
            datos = {}
        if not isinstance(datos, dict) or not datos.get("correo") or not datos.get("clave"):
            return self.responder(400, {"error": 'Envía un JSON con "correo" y "clave".'})
        if datos["correo"].lower() != CORREO or datos["clave"] != CLAVE:
            return self.responder(401, {"error": "Correo o contraseña incorrectos."})
        self.responder(200, {"token": TOKEN, "tipo": "Bearer", "expira_en": 28800,
                             "usuario": {"nombre": "Integración", "rol": "administrador"}})

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.rstrip("/") != "/api/facturas":
            return self.responder(404, {"error": "La ruta no existe."})
        if self.headers.get("Authorization", "") != f"Bearer {TOKEN}":
            return self.responder(401, {"error": "Falta el token. Envía el encabezado Authorization: Bearer <token>."})
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        tipo = q.get("tipo") or None
        if tipo not in (None, "venta", "compra"):
            return self.responder(400, {"error": 'El tipo debe ser "venta" o "compra", o no enviarlo para traer las dos.'})
        try:
            hoy = date.today()
            hasta = date.fromisoformat(q["hasta"]) if q.get("hasta") else hoy
            desde = date.fromisoformat(q["desde"]) if q.get("desde") else hoy.replace(day=1)
        except ValueError:
            return self.responder(400, {"error": "Las fechas deben tener el formato AAAA-MM-DD."})
        if desde > hasta:
            return self.responder(400, {"error": "La fecha inicial no puede ser posterior a la final."})
        self.responder(200, facturas(desde, hasta, tipo))


if __name__ == "__main__":
    print(f"Simulador de RepuAuto en http://127.0.0.1:{PUERTO}/api  (Ctrl+C para salir)")
    print(f"Credenciales: {CORREO} / {CLAVE}")
    ThreadingHTTPServer(("127.0.0.1", PUERTO), Manejador).serve_forever()
