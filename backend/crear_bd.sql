-- =====================================================================
-- crear_bd.sql
-- Crea la base de datos local y el usuario que usa Django.
-- Este script NO crea las tablas: las crea Django con
--     uv run python manage.py migrate
-- (incluye la tabla usuario con email unico y password hasheado).
-- =====================================================================
--
-- ANTES DE EJECUTARLO:
--   1. Cambia 'django_tunombre' por el nombre de usuario que quieras
--      (debe coincidir con USER en backend/Proyecto_UD1/settings.py).
--   2. Cambia 'cambia_esta_clave' por tu propia contrasena
--      (debe coincidir con PASSWORD en settings.py).
--      Evita usar n con tilde (enie) o tildes en la clave.
--
-- COMO EJECUTARLO (elige una opcion):
--
--   Opcion A - psql (todo de una vez), desde la carpeta backend/:
--       psql -U postgres -f crear_bd.sql
--
--   Opcion B - pgAdmin (en 2 pasos, porque CREATE DATABASE no se puede
--   ejecutar junto a otras sentencias):
--       Paso 1. Query Tool sobre la base "postgres": ejecuta SOLO el
--               bloque PASO 1, una sentencia a la vez.
--       Paso 2. Query Tool sobre la base "tienda" (refresca el arbol
--               para verla): ejecuta SOLO el bloque PASO 2.
--
-- Si la base "tienda" o el usuario ya existen, PostgreSQL mostrara un
-- error de "ya existe": es inofensivo, continua con el siguiente paso.
-- =====================================================================


-- ---------------------------- PASO 1 ---------------------------------
-- (conectado a la base "postgres")

CREATE ROLE django_tunombre WITH LOGIN PASSWORD 'cambia_esta_clave';

CREATE DATABASE tienda OWNER django_tunombre ENCODING 'UTF8';


-- ---------------------------- PASO 2 ---------------------------------
-- (conectado a la base "tienda")
-- Solo en psql: la siguiente linea cambia de base automaticamente.
-- En pgAdmin, borra o ignora esa linea y ejecuta el resto sobre "tienda".

\connect tienda

-- Permisos sobre el esquema public (necesario en PostgreSQL 15 o superior;
-- sin esto, "migrate" falla con "permiso denegado al esquema public").
GRANT ALL ON SCHEMA public TO django_tunombre;
ALTER SCHEMA public OWNER TO django_tunombre;


-- ---------------------------- VERIFICAR ------------------------------
-- Opcional: lista las tablas (al inicio estara vacio; despues de
-- "migrate" veras las tablas inventario_* y las internas de Django).
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' ORDER BY table_name;
