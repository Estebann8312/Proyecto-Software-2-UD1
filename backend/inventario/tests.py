"""
Pruebas de seguridad y consistencia del backend.

Correr con:
    uv run python manage.py test inventario
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import (
    CategoriaPieza,
    Cliente,
    LoteCompra,
    Pieza,
    Proveedor,
    Usuario,
    Venta,
)

User = get_user_model()
CLAVE = "Clave.Segura.2026"


# Hasher rápido solo para pruebas (el real es lento a propósito).
@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BaseAPITest(TestCase):
    """Datos comunes: un admin, dos vendedores, un cliente registrado y una pieza."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_user, cls.admin = cls.crear_empleado("admin", "administrador")
        cls.vend_user, cls.vendedor = cls.crear_empleado("vendedor", "vendedor")
        cls.vend2_user, cls.vendedor2 = cls.crear_empleado("vendedor2", "vendedor")

        cls.cliente_user = User.objects.create_user("cliente", "cliente@mail.com", CLAVE)
        cls.cliente = Cliente.objects.create(
            user=cls.cliente_user, nombres="Cli", apellidos="Ente", email="cliente@mail.com"
        )

        cls.categoria = CategoriaPieza.objects.create(nombre="CPU")
        cls.proveedor = Proveedor.objects.create(nombre="Mayorista")
        cls.pieza = Pieza.objects.create(
            nombre="Ryzen 5", id_categoria=cls.categoria, condicion="nueva",
            precio_venta=Decimal("100.00"), stock_actual=10,
        )

    @staticmethod
    def crear_empleado(username, rol):
        user = User.objects.create_user(username, f"{username}@tienda.com", CLAVE)
        empleado = Usuario.objects.create(
            user=user, nombres=username, apellidos="Test",
            email=f"{username}@tienda.com", rol=rol,
        )
        return user, empleado

    def setUp(self):
        cache.clear()  # reinicia los contadores de límite de intentos
        self.anon = APIClient()
        self.admin_api = self.cliente_api_para(self.admin_user)
        self.vend_api = self.cliente_api_para(self.vend_user)
        self.cli_api = self.cliente_api_para(self.cliente_user)

    @staticmethod
    def cliente_api_para(user):
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    def registrar(self, **extra):
        datos = {
            "username": "nuevo", "email": "nuevo@mail.com", "password": CLAVE,
            "first_name": "Nu", "last_name": "Evo",
        }
        datos.update(extra)
        return self.anon.post("/api/auth/register/", datos, format="json")

    def payload_venta(self, cantidad=1, **extra):
        datos = {
            "id_cliente": self.cliente.pk,
            "metodo_pago": "efectivo",
            "detalles": [{"id_pieza": self.pieza.pk, "cantidad": cantidad}],
        }
        datos.update(extra)
        return datos


# ---------------------------------------------------------------------------
# Autenticación y registro
# ---------------------------------------------------------------------------

class RegistroTests(BaseAPITest):

    def test_registro_crea_cliente_no_empleado(self):
        r = self.registrar()
        self.assertEqual(r.status_code, 201)
        user = User.objects.get(username="nuevo")
        self.assertTrue(Cliente.objects.filter(user=user).exists())
        self.assertFalse(Usuario.objects.filter(user=user).exists())

    def test_no_se_puede_registrar_con_email_de_empleado(self):
        # Antes: registrarse con el correo de un empleado heredaba su rol.
        r = self.registrar(email="admin@tienda.com")
        self.assertEqual(r.status_code, 400)

    def test_empleado_sin_cuenta_no_es_suplantable(self):
        Usuario.objects.create(
            nombres="Sin", apellidos="Cuenta", email="sincuenta@tienda.com", rol="administrador"
        )
        r = self.registrar(email="SinCuenta@Tienda.com")
        self.assertEqual(r.status_code, 400)

    def test_email_no_distingue_mayusculas(self):
        r = self.registrar(email="CLIENTE@MAIL.COM")
        self.assertEqual(r.status_code, 400)

    def test_email_se_guarda_en_minusculas(self):
        self.registrar(email="Mixto@Mail.COM")
        self.assertEqual(User.objects.get(username="nuevo").email, "mixto@mail.com")

    def test_rechaza_contrasenas_debiles(self):
        for debil in ["password", "12345678", "corta"]:
            r = self.registrar(password=debil)
            self.assertEqual(r.status_code, 400, debil)
            self.assertIn("password", r.data)

    def test_username_duplicado_sin_distinguir_mayusculas(self):
        r = self.registrar(username="CLIENTE", email="otro@mail.com")
        self.assertEqual(r.status_code, 400)


class LoginTests(BaseAPITest):

    def test_login_devuelve_rol(self):
        for username, rol in [("admin", "administrador"), ("vendedor", "vendedor"), ("cliente", "cliente")]:
            r = self.anon.post("/api/auth/login/", {"username": username, "password": CLAVE}, format="json")
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.data["rol"], rol)
            self.assertIn("access", r.data)
            self.assertIn("refresh", r.data)

    def test_me_devuelve_rol(self):
        self.assertEqual(self.admin_api.get("/api/auth/me/").data["rol"], "administrador")
        r = self.cli_api.get("/api/auth/me/")
        self.assertEqual(r.data["rol"], "cliente")
        self.assertEqual(r.data["id_cliente"], self.cliente.pk)
        self.assertEqual(self.anon.get("/api/auth/me/").status_code, 401)

    def test_limite_de_intentos_de_login(self):
        codigos = [
            self.anon.post("/api/auth/login/", {"username": "admin", "password": "mala"}, format="json").status_code
            for _ in range(12)
        ]
        self.assertIn(429, codigos)


# ---------------------------------------------------------------------------
# Escalamiento de privilegios
# ---------------------------------------------------------------------------

class PermisosUsuariosTests(BaseAPITest):

    def test_cliente_no_puede_ver_ni_crear_empleados(self):
        self.assertEqual(self.cli_api.get("/api/usuarios/").status_code, 403)
        r = self.cli_api.post("/api/usuarios/", {
            "username": "yo", "password": CLAVE, "nombres": "c", "apellidos": "c",
            "email": "yo@mail.com", "rol": "administrador",
        }, format="json")
        self.assertEqual(r.status_code, 403)

    def test_vendedor_no_puede_gestionar_empleados(self):
        self.assertEqual(self.vend_api.get("/api/usuarios/").status_code, 403)
        r = self.vend_api.patch(f"/api/usuarios/{self.vendedor.pk}/", {"rol": "administrador"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.vendedor.refresh_from_db()
        self.assertEqual(self.vendedor.rol, "vendedor")

    def test_admin_crea_empleado_con_cuenta(self):
        r = self.admin_api.post("/api/usuarios/", {
            "username": "nueva.vend", "password": CLAVE, "nombres": "Nueva", "apellidos": "Vend",
            "email": "Nueva@Tienda.com", "rol": "vendedor",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertNotIn("password", r.data)
        empleado = Usuario.objects.get(pk=r.data["id_usuario"])
        self.assertEqual(empleado.user.username, "nueva.vend")
        self.assertEqual(empleado.email, "nueva@tienda.com")
        self.assertTrue(empleado.user.check_password(CLAVE))

    def test_admin_cambia_contrasena_de_empleado(self):
        r = self.admin_api.patch(f"/api/usuarios/{self.vendedor.pk}/", {"password": "Otra.Clave.2026"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.vend_user.refresh_from_db()
        self.assertTrue(self.vend_user.check_password("Otra.Clave.2026"))

    def test_crear_empleado_con_email_existente_falla(self):
        r = self.admin_api.post("/api/usuarios/", {
            "username": "x", "password": CLAVE, "nombres": "x", "apellidos": "x",
            "email": "CLIENTE@mail.com", "rol": "vendedor",
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_admin_no_puede_eliminarse_a_si_mismo(self):
        r = self.admin_api.delete(f"/api/usuarios/{self.admin.pk}/")
        self.assertEqual(r.status_code, 400)

    def test_eliminar_empleado_elimina_su_cuenta(self):
        r = self.admin_api.delete(f"/api/usuarios/{self.vendedor2.pk}/")
        self.assertEqual(r.status_code, 204)
        self.assertFalse(User.objects.filter(pk=self.vend2_user.pk).exists())

    def test_eliminar_empleado_con_ventas_da_409(self):
        self.vend_api.post("/api/ventas/", self.payload_venta(), format="json")
        r = self.admin_api.delete(f"/api/usuarios/{self.vendedor.pk}/")
        self.assertEqual(r.status_code, 409)


class PermisosCatalogoTests(BaseAPITest):

    def test_categorias_lectura_publica_escritura_admin(self):
        self.assertEqual(self.anon.get("/api/categorias/").status_code, 200)
        for api in (self.cli_api, self.vend_api):
            self.assertEqual(api.post("/api/categorias/", {"nombre": "Spam"}, format="json").status_code, 403)
        self.assertEqual(self.admin_api.post("/api/categorias/", {"nombre": "GPU"}, format="json").status_code, 201)

    def test_proveedores_solo_empleados_y_escritura_admin(self):
        self.assertEqual(self.cli_api.get("/api/proveedores/").status_code, 403)
        self.assertEqual(self.vend_api.get("/api/proveedores/").status_code, 200)
        r = self.vend_api.patch(f"/api/proveedores/{self.proveedor.pk}/", {"nombre": "HACKED"}, format="json")
        self.assertEqual(r.status_code, 403)
        r = self.cli_api.patch(f"/api/proveedores/{self.proveedor.pk}/", {"nombre": "HACKED"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.proveedor.refresh_from_db()
        self.assertEqual(self.proveedor.nombre, "Mayorista")

    def test_clientes_solo_empleados(self):
        self.assertEqual(self.cli_api.get("/api/clientes/").status_code, 403)
        self.assertEqual(self.anon.get("/api/clientes/").status_code, 401)
        self.assertEqual(self.vend_api.get("/api/clientes/").status_code, 200)

    def test_catalogo_publico_oculta_stock_y_costos(self):
        for api in (self.anon, self.cli_api):
            pieza = api.get("/api/piezas/").data[0]
            self.assertNotIn("stock_actual", pieza)
            self.assertNotIn("lotes", pieza)
            self.assertTrue(pieza["en_stock"])

    def test_empleado_ve_stock_real(self):
        pieza = self.vend_api.get("/api/piezas/").data[0]
        self.assertEqual(pieza["stock_actual"], 10)

    def test_solo_admin_crea_piezas(self):
        datos = {"nombre": "X", "id_categoria": self.categoria.pk, "condicion": "nueva", "precio_venta": "5"}
        self.assertEqual(self.cli_api.post("/api/piezas/", datos, format="json").status_code, 403)
        self.assertEqual(self.vend_api.post("/api/piezas/", datos, format="json").status_code, 403)
        self.assertEqual(self.admin_api.post("/api/piezas/", datos, format="json").status_code, 201)

    def test_lotes_solo_admin(self):
        datos = {"id_proveedor": self.proveedor.pk, "id_pieza": self.pieza.pk, "cantidad": 5, "costo_unitario": "50"}
        self.assertEqual(self.cli_api.post("/api/lotes/", datos, format="json").status_code, 403)
        self.assertEqual(self.vend_api.post("/api/lotes/", datos, format="json").status_code, 403)
        self.assertEqual(self.vend_api.get("/api/lotes/").status_code, 403)


# ---------------------------------------------------------------------------
# Consistencia de inventario
# ---------------------------------------------------------------------------

class InventarioTests(BaseAPITest):

    def test_stock_no_se_edita_directamente(self):
        r = self.admin_api.patch(f"/api/piezas/{self.pieza.pk}/", {"stock_actual": 99999}, format="json")
        self.assertEqual(r.status_code, 200)
        self.pieza.refresh_from_db()
        self.assertEqual(self.pieza.stock_actual, 10)

    def test_stock_inicial_al_crear_pieza_se_ignora(self):
        r = self.admin_api.post("/api/piezas/", {
            "nombre": "GPU", "id_categoria": self.categoria.pk, "condicion": "nueva",
            "precio_venta": "500", "stock_actual": 50,
        }, format="json")
        self.assertEqual(r.data["stock_actual"], 0)

    def test_lote_suma_stock(self):
        r = self.admin_api.post("/api/lotes/", {
            "id_proveedor": self.proveedor.pk, "id_pieza": self.pieza.pk,
            "cantidad": 5, "costo_unitario": "60",
        }, format="json")
        self.assertEqual(r.status_code, 201)
        self.pieza.refresh_from_db()
        self.assertEqual(self.pieza.stock_actual, 15)

    def test_lotes_no_se_editan_ni_borran(self):
        lote = LoteCompra.objects.create(
            id_proveedor=self.proveedor, id_pieza=self.pieza, cantidad=1, costo_unitario=1
        )
        self.assertEqual(self.admin_api.patch(f"/api/lotes/{lote.pk}/", {"cantidad": 100}, format="json").status_code, 405)
        self.assertEqual(self.admin_api.delete(f"/api/lotes/{lote.pk}/").status_code, 405)

    def test_lote_con_cantidad_cero_o_costo_negativo(self):
        base = {"id_proveedor": self.proveedor.pk, "id_pieza": self.pieza.pk}
        r = self.admin_api.post("/api/lotes/", {**base, "cantidad": 0, "costo_unitario": "1"}, format="json")
        self.assertEqual(r.status_code, 400)
        r = self.admin_api.post("/api/lotes/", {**base, "cantidad": 1, "costo_unitario": "-1"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_precio_negativo_rechazado(self):
        r = self.admin_api.patch(f"/api/piezas/{self.pieza.pk}/", {"precio_venta": "-5"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_borrar_pieza_con_ventas_da_409(self):
        self.vend_api.post("/api/ventas/", self.payload_venta(), format="json")
        r = self.admin_api.delete(f"/api/piezas/{self.pieza.pk}/")
        self.assertEqual(r.status_code, 409)

    def test_borrar_categoria_con_piezas_da_409(self):
        r = self.admin_api.delete(f"/api/categorias/{self.categoria.pk}/")
        self.assertEqual(r.status_code, 409)


# ---------------------------------------------------------------------------
# Ventas
# ---------------------------------------------------------------------------

class VentaTests(BaseAPITest):

    def test_venta_descuenta_stock_y_calcula_total(self):
        r = self.vend_api.post("/api/ventas/", self.payload_venta(cantidad=3), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Decimal(r.data["total"]), Decimal("300.00"))
        self.assertEqual(r.data["estado"], "activa")
        self.pieza.refresh_from_db()
        self.assertEqual(self.pieza.stock_actual, 7)

    def test_vendedor_lo_asigna_el_servidor(self):
        # Antes: un vendedor podía registrar la venta a nombre de otro.
        r = self.vend_api.post(
            "/api/ventas/", self.payload_venta(id_vendedor=self.vendedor2.pk), format="json"
        )
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["id_vendedor"], self.vendedor.pk)

    def test_precio_lo_toma_de_la_pieza(self):
        datos = self.payload_venta()
        datos["detalles"][0]["precio_unitario"] = "0.01"
        r = self.vend_api.post("/api/ventas/", datos, format="json")
        self.assertEqual(Decimal(r.data["total"]), Decimal("100.00"))

    def test_estado_y_total_no_se_pueden_enviar(self):
        r = self.vend_api.post(
            "/api/ventas/", self.payload_venta(estado="anulada", total="1"), format="json"
        )
        self.assertEqual(r.data["estado"], "activa")
        self.assertEqual(Decimal(r.data["total"]), Decimal("100.00"))

    def test_stock_insuficiente_no_deja_rastro(self):
        r = self.vend_api.post("/api/ventas/", self.payload_venta(cantidad=11), format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(Venta.objects.count(), 0)
        self.pieza.refresh_from_db()
        self.assertEqual(self.pieza.stock_actual, 10)

    def test_venta_atomica_con_varias_piezas(self):
        otra = Pieza.objects.create(
            nombre="RAM", id_categoria=self.categoria, condicion="nueva",
            precio_venta=Decimal("50"), stock_actual=1,
        )
        datos = self.payload_venta()
        datos["detalles"] = [
            {"id_pieza": self.pieza.pk, "cantidad": 2},
            {"id_pieza": otra.pk, "cantidad": 5},  # sin stock suficiente
        ]
        r = self.vend_api.post("/api/ventas/", datos, format="json")
        self.assertEqual(r.status_code, 400)
        self.pieza.refresh_from_db()
        self.assertEqual(self.pieza.stock_actual, 10)  # la primera línea se revirtió

    def test_validaciones_de_detalle(self):
        casos = [
            [],  # sin piezas
            [{"id_pieza": self.pieza.pk, "cantidad": 0}],
            [{"id_pieza": self.pieza.pk, "cantidad": 1}, {"id_pieza": self.pieza.pk, "cantidad": 1}],
            [{"id_pieza": 99999, "cantidad": 1}],
        ]
        for detalles in casos:
            r = self.vend_api.post("/api/ventas/", self.payload_venta() | {"detalles": detalles}, format="json")
            self.assertEqual(r.status_code, 400, detalles)

    def test_metodo_pago_invalido(self):
        r = self.vend_api.post(
            "/api/ventas/", self.payload_venta(metodo_pago="<script>alert(1)</script>"), format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_cliente_no_puede_vender_ni_ver_ventas(self):
        self.assertEqual(self.cli_api.post("/api/ventas/", self.payload_venta(), format="json").status_code, 403)
        self.assertEqual(self.cli_api.get("/api/ventas/").status_code, 403)

    def test_ventas_no_se_editan_ni_borran(self):
        venta_id = self.vend_api.post("/api/ventas/", self.payload_venta(), format="json").data["id_venta"]
        self.assertEqual(self.admin_api.patch(f"/api/ventas/{venta_id}/", {"metodo_pago": "efectivo"}, format="json").status_code, 405)
        self.assertEqual(self.admin_api.delete(f"/api/ventas/{venta_id}/").status_code, 405)


class AnulacionTests(BaseAPITest):

    def setUp(self):
        super().setUp()
        r = self.vend_api.post("/api/ventas/", self.payload_venta(cantidad=4), format="json")
        self.venta_id = r.data["id_venta"]

    def test_admin_anula_y_devuelve_stock(self):
        r = self.admin_api.post(f"/api/ventas/{self.venta_id}/anular/")
        self.assertEqual(r.status_code, 200)
        self.pieza.refresh_from_db()
        self.assertEqual(self.pieza.stock_actual, 10)
        self.assertEqual(Venta.objects.get(pk=self.venta_id).estado, "anulada")

    def test_no_se_anula_dos_veces(self):
        self.admin_api.post(f"/api/ventas/{self.venta_id}/anular/")
        r = self.admin_api.post(f"/api/ventas/{self.venta_id}/anular/")
        self.assertEqual(r.status_code, 400)
        self.pieza.refresh_from_db()
        self.assertEqual(self.pieza.stock_actual, 10)  # no devolvió stock dos veces

    def test_vendedor_no_puede_anular(self):
        r = self.vend_api.post(f"/api/ventas/{self.venta_id}/anular/")
        self.assertEqual(r.status_code, 403)

    def test_anular_venta_inexistente_da_404(self):
        r = self.admin_api.post("/api/ventas/99999/anular/")
        self.assertEqual(r.status_code, 404)

    def test_estado_visible_en_consulta(self):
        self.admin_api.post(f"/api/ventas/{self.venta_id}/anular/")
        r = self.vend_api.get(f"/api/ventas/{self.venta_id}/")
        self.assertEqual(r.data["estado"], "anulada")


class ClienteTests(BaseAPITest):

    def test_vendedor_crea_cliente_de_mostrador_sin_email(self):
        r = self.vend_api.post("/api/clientes/", {"nombres": "Mostrador", "apellidos": "X", "email": ""}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIsNone(r.data["email"])

    def test_cliente_con_email_de_empleado_rechazado(self):
        r = self.vend_api.post(
            "/api/clientes/", {"nombres": "a", "apellidos": "b", "email": "ADMIN@tienda.com"}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_no_se_puede_asignar_user_a_cliente(self):
        r = self.vend_api.post(
            "/api/clientes/",
            {"nombres": "a", "apellidos": "b", "user": self.admin_user.pk},
            format="json",
        )
        self.assertIsNone(r.data["user"])
