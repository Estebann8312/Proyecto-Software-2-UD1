# Guía de configuración del entorno

Sistema de inventario y ventas de piezas de computador.

- **Backend:** Django + Django REST Framework + PostgreSQL (carpeta `backend/`)
- **Frontend:** React (carpeta `frontend/`)
- **Dependencias de Python:** se manejan con **uv** (archivos `pyproject.toml` y `uv.lock` en la raíz)

> **Importante:** este proyecto ya **no usa** `venv` + `pip` + `requirements.txt`. Si ves instrucciones antiguas con `pip install`, ignóralas.

---

## 1. Requisitos previos

Instala, si no los tienes:

- **Git** → https://git-scm.com/downloads
- **PostgreSQL** (incluye pgAdmin) → https://www.postgresql.org/download
- **uv** (PowerShell):
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  Cierra y vuelve a abrir la terminal, y verifica con:
  ```powershell
  uv --version
  ```
- **Node.js** (solo si vas a trabajar en el frontend) → https://nodejs.org

No necesitas instalar Python a mano: `uv` descarga la versión que pide el proyecto (`.python-version`).

## 2. Clonar el repositorio

```powershell
git clone https://github.com/Estebann8312/Proyecto-Software-2-UD1
cd Proyecto-Software-2-UD1
```

## 3. Instalar las dependencias del backend

Desde la **raíz** del proyecto (donde está `pyproject.toml`):

```powershell
uv sync
```

Esto crea la carpeta `.venv` y deja instaladas exactamente las mismas versiones que usa todo el equipo (según `uv.lock`). No hay que activar el entorno: se usa con `uv run`.

## 4. Crear tu base de datos local en PostgreSQL

Cada integrante usa **su propia base de datos local** (no se comparte una entre todos). Para crearla usa el script `backend/crear_bd.sql`:

1. Ábrelo y cambia los dos valores de ejemplo:
   - `django_tunombre` → el usuario que quieras usar.
   - `cambia_esta_clave` → tu contraseña (evita la ñ y las tildes).
2. Ejecútalo, con **una** de estas opciones:
   - **psql** (todo de una vez), desde la carpeta `backend/`:
     ```powershell
     psql -U postgres -f crear_bd.sql
     ```
   - **pgAdmin** (en dos pasos): ejecuta el bloque *PASO 1* sobre la base `postgres` (una sentencia a la vez) y el bloque *PASO 2* sobre la base `tienda`.

El script crea la base `tienda`, el usuario y los permisos sobre el esquema `public` (necesarios en PostgreSQL 15 o superior; sin ellos las migraciones fallan con "permiso denegado al esquema public").

> El script **no crea las tablas**: de eso se encarga Django con `migrate` (paso 6). No uses el antiguo `script-bd-inventario-ventas.sql`, que crea tablas con otros nombres y choca con las de Django.

## 5. Configurar la conexión (`.env`)

La configuración ya **no** se edita en `settings.py`: se lee del archivo `backend/.env`, que no se sube al repositorio.

```powershell
cd backend
copy .env.example .env
```

Abre `backend/.env` y pon **tus** datos (los mismos del paso 4). Para desarrollo deja `DJANGO_DEBUG=True`; si lo omites, Django arranca con `DEBUG=False` por seguridad y el panel `/admin/` se verá sin estilos.

Para generar una `DJANGO_SECRET_KEY`:

```powershell
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

La configuración de CORS ya viene incluida en `settings.py` (puertos 3000 y 5173).

## 6. Crear las tablas

```powershell
cd backend
uv run python manage.py migrate
```

## 7. Crear tu superusuario (acceso a `/admin/`)

```powershell
uv run python manage.py createsuperuser
```
> El superusuario sirve para el panel `/admin/` de Django, pero **no tiene rol en la API**. Para que un usuario sea administrador o vendedor en la API, debe existir un registro `Usuario` vinculado a su cuenta (campo `user`). Lo más fácil es cargar los datos de prueba (paso 9) o, ya con un administrador, crear empleados con `POST /api/usuarios/`.

## 8. Levantar el servidor

```powershell
uv run python manage.py runserver
```

Prueba en el navegador:

- `http://127.0.0.1:8000/admin/` → panel de administración
- `http://127.0.0.1:8000/api/piezas/` → API (debe responder JSON, aunque sea `[]`)

> La ruta `http://127.0.0.1:8000/` a secas da 404. Es normal: no hay nada definido en la raíz.

## 9. (Opcional) Cargar datos de prueba

En `backend/` hay un script `poblar_datos.py` con datos de ejemplo. Si el propio script indica otra forma de correrlo, sigue la del script. Si no, una forma que funciona en PowerShell:

```powershell
$env:PYTHONUTF8=1
uv run python manage.py shell -c "exec(open('poblar_datos.py', encoding='utf-8').read())"
```

> No uses `Get-Content poblar_datos.py | ... shell`: PowerShell envía el archivo línea por línea y falla con `IndentationError`.

El script crea cuentas listas para probar (el *username* es la parte del correo antes de la `@`):

| Rol | Username | Contraseña |
|---|---|---|
| Administrador | `carlos.admin` | `Empleado.2026` |
| Vendedor | `laura.ventas` | `Empleado.2026` |
| Cliente | `andres.silva` | `Cliente.2026` |

> Ejecútalo sobre una base **vacía**. Para vaciarla: `uv run python manage.py flush --no-input` (borra todos los datos, incluido el superusuario).

## 9.1 Correr las pruebas

La primera vez, dale a tu usuario permiso para crear la base temporal de pruebas. En pgAdmin, Query Tool sobre la base `postgres`:

```sql
ALTER USER django_tunombre CREATEDB;
```

Luego:

```powershell
uv run python manage.py test inventario
```

Todas deben pasar antes de abrir un Pull Request.

## 10. Frontend (React)

> _Pendiente de completar por quien desarrolló el frontend: comandos para instalar (`npm install`) y levantar (`npm run dev`), y puerto en el que corre._

---

## Comandos de uv que vas a usar seguido

| Qué quieres hacer | Comando (desde la raíz o desde `backend/`) |
|---|---|
| Instalar todo lo del proyecto | `uv sync` |
| Agregar una librería nueva | `uv add nombre-libreria` |
| Quitar una librería | `uv remove nombre-libreria` |
| Correr un comando de Django | `uv run python manage.py <comando>` |

Cuando agregues una librería con `uv add`, se modifican `pyproject.toml` y `uv.lock`: **commitea ambos** para que el resto del equipo reciba el cambio con un `uv sync`.

## Cómo contribuir (flujo con ramas)

**No trabajes directamente sobre `main`.** Antes de empezar una tarea:

```powershell
git checkout main
git pull origin main
git checkout -b feature/nombre-de-tu-tarea
```

Haz tus commits en esa rama y, al terminar:

```powershell
git push origin feature/nombre-de-tu-tarea
```

Luego abre un **Pull Request** en GitHub hacia `main` para que alguien del equipo lo revise antes de integrarlo.

Después de hacer `git pull`, si el commit trae cambios en los modelos o en las dependencias, corre:

```powershell
uv sync
uv run python manage.py migrate
```

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `ModuleNotFoundError: No module named 'django'` | Estás usando el Python global. Corre los comandos con `uv run ...` y ejecuta `uv sync` en la raíz. |
| `permiso denegado al esquema public` al migrar | Falta ejecutar el *PASO 2* de `crear_bd.sql` (permisos sobre el esquema `public`). |
| `could not connect to server` | PostgreSQL no está corriendo. Revisa en "Servicios" de Windows que esté en ejecución. |
| Errores de CORS en la consola del navegador | Falta o está mal la configuración de CORS (paso 5), o el puerto del frontend no está en `CORS_ALLOWED_ORIGINS`. |
| VS Code subraya los `import django` | Selecciona el intérprete `.venv` de la raíz: `Ctrl+Shift+P` → **Python: Select Interpreter**. |
| Borrar una carpeta `venv` vieja da "Access denied" | Algún proceso la usa. Cierra VS Code y las terminales, y reintenta. La carpeta `backend/venv` del flujo anterior ya no se usa. |
| `KeyError: 'DJANGO_SECRET_KEY'` (o `DB_NAME`) | Falta el archivo `backend/.env` o le falta esa variable (paso 5). |
| `permission denied to create database` al correr pruebas | Falta el permiso del paso 9.1: `ALTER USER django_tunombre CREATEDB;` |
| `IndentationError` al cargar datos de prueba | Usaste `Get-Content ... \|`. Usa el comando con `exec(...)` del paso 9. |

## Checklist final

- [ ] `uv --version` responde
- [ ] `uv sync` corre sin errores
- [ ] `uv run python manage.py runserver` levanta el servidor
- [ ] `/admin/` carga y entras con tu superusuario
- [ ] `/api/piezas/` responde JSON
- [ ] `git status` **no** muestra `.venv/` ni `venv/` como archivos nuevos
