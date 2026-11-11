# Contrato de integración entre sedes

**PC Stock** (grupo UD1, Django) y **RepuAuto** (Flask, [repositorio](https://github.com/Thiago3108/repuauto)).

Cada sede publica sus **facturas de venta y de compra** y su **inventario** en JSON con el mismo
formato. El **aplicativo consolidador** los pide a las dos sedes y los junta. Las dos sedes tienen
el suyo: en PC Stock es la pantalla **Sedes** del administrador (pestañas Facturas e Inventario) y en
RepuAuto, su página **Consolidado de sedes**.

El formato es el que propuso RepuAuto en su [docs/API.md](https://github.com/Thiago3108/repuauto/blob/main/docs/API.md).
PC Stock lo adoptó **sin cambios**, así que las dos API se usan exactamente igual.

## 1. Endpoints (iguales en las dos sedes)

| Método y ruta | Qué hace |
|---|---|
| `POST /api/login` | Recibe `{"correo": "...", "clave": "..."}` de un **administrador** y devuelve un token |
| `GET /api/facturas` | Facturas de la sede. Parámetros opcionales `desde`, `hasta` (`AAAA-MM-DD`) y `tipo` (`venta` o `compra`) |
| `GET /api/inventario` | Inventario de hoy de la sede. Parámetro opcional `estado` (`en_stock`, `stock_bajo` o `agotado`) |

- Las peticiones a `/api/facturas` y `/api/inventario` llevan el encabezado `Authorization: Bearer <token>`.
- Sin fechas se toma el mes actual: del día 1 a hoy. `hasta` se incluye completo.
- Todo responde JSON, también los errores: `{"error": "mensaje"}`.

| Sede | Dirección local | Puerto |
|---|---|---|
| PC Stock | `http://127.0.0.1:8000/api` | 8000 (Django) |
| RepuAuto | `http://127.0.0.1:5000/api` | 5000 (Flask) |

### Respuesta de `POST /api/login`

```json
{
  "token": "eyJ...",
  "tipo": "Bearer",
  "expira_en": 28800,
  "usuario": {"nombre": "Carlos Andrés Mendoza Riaño", "rol": "administrador"}
}
```

`expira_en` está en segundos (8 horas). Cuando vence, se pide otro token.

### Respuesta de `GET /api/facturas`

```json
{
  "sucursal": "PC Stock",
  "desde": "2026-10-01",
  "hasta": "2026-10-31",
  "moneda": "COP",
  "iva_porcentaje": 19,
  "resumen": {
    "venta":  {"cantidad": 1, "subtotal": "521008.40", "iva": "98991.60", "total": "620000.00"},
    "compra": {"cantidad": 1, "subtotal": "3865546.22", "iva": "734453.78", "total": "4600000.00"}
  },
  "facturas": [
    {
      "tipo": "compra",
      "numero": "C-000012",
      "fecha": "2026-10-04T00:00:00-05:00",
      "tercero": {"documento": "900456789-1", "nombre": "TechDistribuciones Mayorista S.A.S."},
      "subtotal": "3865546.22",
      "iva": "734453.78",
      "total": "4600000.00"
    },
    {
      "tipo": "venta",
      "numero": "V-000007",
      "fecha": "2026-10-30T10:15:00-05:00",
      "tercero": {"documento": "1098000001", "nombre": "Andrés Felipe Silva Vega"},
      "subtotal": "521008.40",
      "iva": "98991.60",
      "total": "620000.00"
    }
  ]
}
```

### Respuesta de `GET /api/inventario`

```json
{
  "sucursal": "PC Stock",
  "fecha": "2026-11-10T19:20:06-05:00",
  "moneda": "COP",
  "resumen": {"productos": 23, "unidades": 214, "valor": "109726000.00", "en_stock": 22, "stock_bajo": 1, "agotado": 0},
  "productos": [
    {
      "codigo": "PZ-000039",
      "nombre": "Crucial BX500 480GB SATA 2.5''",
      "categoria": "Almacenamiento (SSD/HDD)",
      "marca": "Crucial",
      "stock": 17,
      "stock_minimo": 4,
      "precio_venta": "136000.00",
      "valor": "2312000.00",
      "estado": "en_stock"
    }
  ]
}
```

- **Estado:** `agotado` si el stock es 0, `stock_bajo` si es menor que `stock_minimo` y `en_stock` en los
  demás casos.
- **Valor:** stock × precio de venta (con IVA incluido).
- **Resumen:** siempre de todo el inventario, aunque se filtre por `estado`.
- **Orden:** por categoría y nombre.

Cómo encaja PC Stock en ese formato (que viene de RepuAuto):

| Campo | En RepuAuto | En PC Stock |
|---|---|---|
| `codigo` | Código del repuesto (`FRE-DIS-011`) | Se arma con el id de la pieza: `PZ-000039` |
| `marca` | Marca del repuesto | Marca de la pieza; si no tiene, `"Sin marca"` |
| `stock_minimo` | Mínimo de cada repuesto | **4 para todas las piezas**: PC Stock marca stock bajo con 3 unidades o menos, y con la regla "menor que el mínimo" eso equivale a un mínimo de 4 |
| Productos | Solo los activos | Todas las piezas (PC Stock no las desactiva) |

### Errores

| Código | Cuándo |
|---|---|
| `400` | Falta el correo o la clave, una fecha está mal escrita, `desde` va después de `hasta` o el `tipo` no existe |
| `401` | Credenciales incorrectas, falta el token, el token fue alterado o ya venció |
| `403` | La cuenta no es de administrador |

## 2. Reglas de los datos

- **Ventas:** solo las efectivas. En RepuAuto son las *Completadas*; en PC Stock, las *activas*.
  Las pendientes, canceladas o anuladas **no se envían**.
- **Compras:** todas las compras a proveedores. En PC Stock cada **lote de compra** es una factura de compra.
- **Tercero:** en las ventas, el cliente con su cédula; en las compras, el proveedor con su NIT.
- **Número:** `V-` para ventas y `C-` para compras, con 6 dígitos (`V-000123`). Dos sedes pueden
  tener el mismo número: la factura se identifica por **`sucursal` + `numero`**.
- **IVA incluido** en el total: `subtotal = total / (1 + iva_porcentaje / 100)` redondeado a centavos,
  e `iva = total − subtotal`. Los dos suman exactamente el total.
- **Dinero:** texto con 2 decimales (`"620000.00"`), en pesos colombianos.
- **Fechas:** ISO 8601 con la hora de Colombia (`-05:00`). Si solo hay fecha (los lotes de PC Stock),
  la hora es `00:00:00`.
- **Orden:** de la factura más antigua a la más reciente.

## 3. Decisiones sobre los puntos que estaban pendientes

RepuAuto dejó cinco puntos por acordar. Para no frenar el trabajo, PC Stock propone esto.
**Si RepuAuto no responde lo contrario, se toma como acordado.**

| Punto | Decisión |
|---|---|
| IVA | 19 % incluido en el precio, en las dos sedes |
| Numeración | `V-` / `C-` con 6 dígitos; se distingue la sede por `sucursal` |
| Nombre de cada sede | `PC Stock` y `Bucaramanga` (el valor por defecto de RepuAuto). Cada uno lo cambia en su `.env` |
| Quién hace el consolidador | **PC Stock**, ya construido (pantalla **Sedes**). Detalle en la sección 4 |
| Dónde se publican las API | En el **computador de cada equipo**, expuestas a internet con **ngrok** y un dominio fijo. Detalle en la sección 5 |

Dos casos que el formato original no cubría:

- **Venta sin cédula** (PC Stock permite clientes sin documento): se envía `"documento": "222222222222"`,
  el código de **consumidor final** de la DIAN.
- **Proveedor sin NIT:** se envía `"documento": null`. PC Stock ya pide el NIT al registrar proveedores.

## 4. El aplicativo consolidador

**Lo hace PC Stock y ya está listo.** No es una tercera aplicación: es la pantalla **Sedes** dentro de
PC Stock, solo para administradores. Se decidió así porque:

- Ya existía la API de PC Stock y su pantalla de reportes; agregar el consolidador ahí no exige otro
  servidor ni otra base de datos que haya que desplegar y mantener.
- RepuAuto no tiene que escribir código nuevo: su API ya entrega lo necesario.
- Cada sede sigue siendo dueña de sus datos: el consolidador **solo lee** facturas, no copia ni modifica
  nada en la otra sede.

Cómo funciona:

1. El administrador de PC Stock elige un rango de fechas en **Sedes**.
2. El servidor de PC Stock (no el navegador) inicia sesión en la API de RepuAuto, pide sus facturas y
   calcula las de PC Stock.
3. Muestra los totales por sede, el total de las dos, el IVA por pagar y la lista de facturas con la sede
   de cada una. Se descarga en CSV.
4. Si RepuAuto no responde, muestra PC Stock y un aviso; nunca se cae la pantalla.

**Para la sustentación de RepuAuto:** pueden mostrar el consolidado entrando a PC Stock con una cuenta de
administrador que les damos, o hacer su propio consolidador con nuestra API, que tiene el mismo formato.

## 5. Despliegue de las API

**Cada equipo corre su aplicación en su propio computador y la expone a internet con
[ngrok](https://ngrok.com).** No se usa un servidor en la nube: obligaría a montar dos bases de datos
PostgreSQL y dos aplicaciones más a días de la entrega, y para una demo de clase no aporta nada.

| | RepuAuto | PC Stock |
|---|---|---|
| ¿Tiene que exponerse? | **Sí**: el consolidador de PC Stock la consulta | Solo si RepuAuto quiere consultar nuestras facturas |
| Comando | `flask run` y `ngrok http --url=SU-DOMINIO 5000` | `uv run python manage.py runserver` y `ngrok http --url=NUESTRO-DOMINIO 8000` |
| URL que se comparte | `https://SU-DOMINIO/api` | `https://NUESTRO-DOMINIO/api` |

Reglas para que funcione el día de la demo:

- **Dominio fijo.** Cada cuenta gratis de ngrok trae un dominio estático (en el panel de ngrok:
  *Domains*). Con `--url=` la dirección no cambia aunque se reinicie ngrok, así que se comparte **una
  sola vez**.
- **Página de aviso de ngrok.** La versión gratis puede responder con una página HTML de aviso. PC Stock
  envía el encabezado `ngrok-skip-browser-warning` para saltarla. Si RepuAuto consulta nuestra API,
  debe enviar el mismo encabezado.
- **Hosts permitidos.** Para exponer PC Stock hay que agregar `.ngrok-free.dev` y `.ngrok-free.app` (los dominios gratis de ngrok; o el que se
  use) a `DJANGO_ALLOWED_HOSTS` en `backend/.env`.
- **Solo funciona con el computador prendido**, la app corriendo y ngrok abierto.
- **Prueba previa:** conectarse al menos una vez **antes** de la sustentación.

**Plan B** si el día de la demo falla la conexión entre los dos computadores:

1. La pantalla Sedes sigue funcionando con PC Stock y muestra que RepuAuto no responde, lo que también
   demuestra el manejo de errores.
2. Para mostrar las dos sedes juntas se usa `backend/simular_repuauto.py`, que responde con el formato
   exacto de RepuAuto (sección 8).

## 6. Qué hace cada equipo

### PC Stock (hecho)

- [x] `POST /api/login`, `GET /api/facturas` y `GET /api/inventario` con el formato de esta guía
      (`backend/inventario/integraciones/`).
- [x] El token de integración **solo sirve para leer facturas e inventario**: no permite usar el resto de la API.
- [x] Pestaña **Inventario** en Sedes: valor, productos y estado del stock por sede y combinados, y la lista
      de productos de las dos sedes con búsqueda, filtros y CSV (`GET /api/consolidado/inventario/`).
- [x] Marca en las piezas (migración 0008).
- [x] Consolidador: `GET /api/consolidado/` y la pantalla **Sedes**, que muestra los totales por sede,
      el total de las dos, el IVA y la lista de facturas, con descarga en CSV.
- [x] Si RepuAuto no responde, el consolidado sigue funcionando con PC Stock y avisa qué pasó.
- [x] NIT en los proveedores.
- [x] Pruebas automáticas del formato y un simulador de la API de RepuAuto (`backend/simular_repuauto.py`).

### RepuAuto (lo mínimo)

1. Confirmar este contrato, o decir qué punto de la sección 3 cambiarían.
2. Crear una cuenta de **administrador** para la integración y pasar el **correo y la clave por privado**
   (no por el grupo ni por el repositorio).
3. Reservar su dominio fijo de ngrok y pasarnos la URL **una vez** (sección 5).
4. Hacer una prueba de conexión con nosotros antes de la sustentación (10 minutos).

**Opcional:** si quieren ver las facturas de PC Stock desde su sistema, PC Stock les pasa una cuenta de
administrador y la URL de ngrok. Como el formato es el mismo, pueden reutilizar su propio código.

## 7. Configuración de PC Stock (`backend/.env`)

| Variable | Por defecto | Para qué |
|---|---|---|
| `INTEGRACION_SUCURSAL` | `PC Stock` | Nombre de esta sede en `/api/facturas` |
| `INTEGRACION_IVA` | `19` | Porcentaje de IVA incluido en los precios |
| `INTEGRACION_TOKEN_HORAS` | `8` | Cuánto dura el token de `/api/login` |
| `REPUAUTO_URL` | vacío | Dirección de la API de RepuAuto, por ejemplo `https://xxxx.ngrok-free.dev/api` |
| `REPUAUTO_CORREO` / `REPUAUTO_CLAVE` | vacío | Cuenta de administrador que nos dé RepuAuto |
| `REPUAUTO_TIMEOUT` | `6` | Segundos máximos de espera |

Sin `REPUAUTO_URL`, la pantalla Sedes muestra solo PC Stock y dice qué falta configurar.

## 8. Probar sin depender de RepuAuto

```powershell
# Terminal 1 (desde backend/): simulador con el formato de RepuAuto
uv run python simular_repuauto.py

# backend/.env
REPUAUTO_URL=http://127.0.0.1:5000/api
REPUAUTO_CORREO=integracion@repuauto.com
REPUAUTO_CLAVE=simulador
```

Después de reiniciar Django, la pantalla **Sedes** muestra las dos sedes. Para probar la API real de
RepuAuto basta con cambiar esas tres variables.

## 9. Lista para el día de la demo

**Antes (una sola vez):**

1. RepuAuto reserva su dominio fijo en ngrok, crea la cuenta de administrador para la integración y nos
   pasa la URL y las credenciales por privado.
2. PC Stock pone en `backend/.env` la URL (terminada en `/api`), el correo y la clave.
3. Prueba de conexión: RepuAuto con `flask run` y ngrok; PC Stock entra a **Sedes** y las dos sedes deben
   salir **En línea**.

**El día de la sustentación:**

1. RepuAuto: `flask run` y `ngrok http --url=SU-DOMINIO 5000`, 10 minutos antes.
2. PC Stock: `runserver` y `npm run dev`; entrar como administrador → **Sedes** → **Actualizar**.
3. Si RepuAuto también nos consulta: `ngrok http --url=NUESTRO-DOMINIO 8000`.
4. Si algo falla: plan B de la sección 5.
