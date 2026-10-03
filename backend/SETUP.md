# Guía de configuración del entorno — Backend (Django + PostgreSQL)

Sigue estos pasos en orden para dejar tu copia del proyecto funcionando localmente.

## 1. Requisitos previos

Instala, si no los tienes:
- **Python 3.12+** → https://python.org/downloads
- **PostgreSQL** (incluye pgAdmin) → https://www.postgresql.org/download
- **Git** → https://git-scm.com/downloads

## 2. Clonar el repositorio

```bash
git clone https://github.com/Estebann8312/Proyecto-Software-2-UD1
cd Proyecto-Software-2-UD1/backend
```

## 3. Crear tu propio entorno virtual

**No** uses el `venv` de otra persona — cada quien crea el suyo localmente (por eso no está en el repositorio):

```bash
python -m venv venv
```

Actívalo:
```bash
# Windows (PowerShell)
venv\Scripts\Activate.ps1

# Mac/Linux
source venv/bin/activate
```

Confirma que veas `(venv)` al inicio de la línea antes de seguir.

## 4. Instalar las dependencias del proyecto

```bash
pip install -r requirements.txt
```

Esto instala exactamente las mismas librerías (Django, DRF, psycopg2, etc.) que usa el resto del equipo.

## 5. Crear tu propia base de datos en PostgreSQL

Cada integrante necesita **su propia base de datos local** — no se comparte una sola entre todos. Usando pgAdmin:

1. Abre pgAdmin, conéctate a tu servidor local.
2. Clic derecho en **Databases → Create → Database...** → nómbrala `tienda`.
3. Clic derecho en **Login/Group Roles → Create → Login/Group Role...**:
   - Nombre: `django_tu_nombre` (o el que prefieras)
   - Pestaña *Definition*: ponle una contraseña.
   - Pestaña *Privileges*: activa **Can login?**
4. Dale permisos sobre el esquema: clic derecho en la base `tienda` → **Properties → Security**, agrega tu usuario con todos los privilegios. O, más simple, en el Query Tool:
   ```sql
   ALTER SCHEMA public OWNER TO django_tu_nombre;
   ```

## 6. Configurar la conexión en `settings.py`

Dentro de `Proyecto_UD1/settings.py`, busca `DATABASES` y reemplaza con **tus propios** datos (no los de otro compañero):

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'tienda',
        'USER': 'django_tu_nombre',
        'PASSWORD': 'tu_contraseña',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

> ⚠️ Esto genera un conflicto si varios suben su contraseña distinta al mismo `settings.py` — si ves que el archivo ya tiene las credenciales de otra persona, es momento de migrar esto a un archivo `.env` (pendiente en el proyecto). Mientras tanto, simplemente cambia los valores localmente sin subir tu contraseña al commitear (evita hacer `git add` sobre ese archivo si lo modificaste solo con tus credenciales).

## 7. Aplicar las migraciones

Esto crea todas las tablas en tu base de datos local, a partir de los modelos que ya están en el repositorio:

```bash
python manage.py migrate
```

## 8. Crear tu propio superusuario (para entrar al panel admin)

```bash
python manage.py createsuperuser
```

## 9. Levantar el servidor

```bash
python manage.py runserver
```

Abre `http://127.0.0.1:8000/admin/` (panel de administración) o `http://127.0.0.1:8000/api/` (API) para confirmar que todo quedó funcionando.

## 10. (Opcional) Poblar tu base de datos con datos de prueba

Si quieres tener datos para probar sin crearlos uno por uno, usa el shell de Django:
```bash
python manage.py shell
```
Y crea registros de prueba (pídele a Esteban el script que ya usamos para poblar categorías, piezas, proveedores, etc.).

---

## Cómo contribuir al código (flujo con ramas)

**Nunca trabajes directamente sobre `main`.** Antes de empezar cualquier tarea:

```bash
git checkout main
git pull origin main
git checkout -b feature/nombre-de-tu-tarea
```

Trabaja y haz commits normalmente en tu rama. Cuando termines:
```bash
git push origin feature/nombre-de-tu-tarea
```

Luego abre un **Pull Request** en GitHub hacia `main` para que el equipo lo revise antes de integrarlo.

## Checklist rápido para saber si quedó bien configurado

- [ ] `python manage.py runserver` corre sin errores
- [ ] `http://127.0.0.1:8000/admin/` carga y puedes iniciar sesión con tu superusuario
- [ ] `http://127.0.0.1:8000/api/piezas/` muestra una respuesta JSON (aunque esté vacía: `[]`)
- [ ] `git status` **no** muestra la carpeta `venv/` como archivo nuevo (si aparece, revisa tu `.gitignore`)
