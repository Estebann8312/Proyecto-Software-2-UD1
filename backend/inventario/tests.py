"""
Pruebas de seguridad y consistencia del backend.

Correr con:
    uv run python manage.py test inventario
"""
from decimal import Decimal
from unittest import mock

import requests

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


class MisComprasTests(BaseAPITest):

    def setUp(self):
        super().setUp()
        self.vend_api.post("/api/ventas/", self.payload_venta(cantidad=2), format="json")
        otro = Cliente.objects.create(nombres="Otro", apellidos="Cliente")
        self.vend_api.post("/api/ventas/", self.payload_venta(id_cliente=otro.pk), format="json")

    def test_cliente_ve_solo_sus_compras(self):
        r = self.cli_api.get("/api/mis-compras/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(r.data[0]["id_cliente"], self.cliente.pk)
        self.assertEqual(r.data[0]["detalles"][0]["cantidad"], 2)

    def test_incluye_ventas_anuladas_con_su_estado(self):
        venta_id = self.cli_api.get("/api/mis-compras/").data[0]["id_venta"]
        self.admin_api.post(f"/api/ventas/{venta_id}/anular/")
        self.assertEqual(self.cli_api.get("/api/mis-compras/").data[0]["estado"], "anulada")

    def test_empleado_sin_ficha_recibe_lista_vacia(self):
        self.assertEqual(self.vend_api.get("/api/mis-compras/").data, [])

    def test_anonimo_no_entra(self):
        self.assertEqual(self.anon.get("/api/mis-compras/").status_code, 401)

    def test_es_solo_lectura(self):
        r = self.cli_api.post("/api/mis-compras/", self.payload_venta(), format="json")
        self.assertEqual(r.status_code, 405)


class ReportesTests(BaseAPITest):
    """Informes del administrador: permisos, rango de fechas y cifras."""

    def setUp(self):
        super().setUp()
        # Lote: 10 unidades a 60 → costo promedio 60 (precio de venta 100).
        self.admin_api.post(
            "/api/lotes/",
            {"id_pieza": self.pieza.pk, "id_proveedor": self.proveedor.pk,
             "cantidad": 10, "costo_unitario": "60.00"},
            format="json",
        )
        self.vend_api.post("/api/ventas/", self.payload_venta(cantidad=3), format="json")
        self.vend_api.post(
            "/api/ventas/", self.payload_venta(cantidad=2, metodo_pago="transferencia"), format="json"
        )
        anulada = self.vend_api.post("/api/ventas/", self.payload_venta(cantidad=1), format="json")
        self.admin_api.post(f"/api/ventas/{anulada.data['id_venta']}/anular/")

    def test_solo_administrador(self):
        self.assertEqual(self.admin_api.get("/api/reportes/").status_code, 200)
        self.assertEqual(self.vend_api.get("/api/reportes/").status_code, 403)
        self.assertEqual(self.cli_api.get("/api/reportes/").status_code, 403)
        self.assertEqual(self.anon.get("/api/reportes/").status_code, 401)

    def test_resumen_cuenta_solo_ventas_activas(self):
        r = self.admin_api.get("/api/reportes/").data["resumen"]
        self.assertEqual(r["ventas"], 2)
        self.assertEqual(r["unidades_vendidas"], 5)
        self.assertEqual(Decimal(r["ingresos"]), Decimal("500.00"))
        self.assertEqual(Decimal(r["ticket_promedio"]), Decimal("250.00"))
        self.assertEqual(r["anuladas"], 1)
        self.assertEqual(Decimal(r["monto_anulado"]), Decimal("100.00"))

    def test_utilidad_con_costo_promedio_de_lotes(self):
        r = self.admin_api.get("/api/reportes/").data["resumen"]
        self.assertEqual(Decimal(r["costo_estimado"]), Decimal("300.00"))
        self.assertEqual(Decimal(r["utilidad_estimada"]), Decimal("200.00"))
        self.assertEqual(r["margen"], 40.0)

    def test_pieza_sin_lotes_no_infla_el_margen(self):
        sin_lote = Pieza.objects.create(
            nombre="Sin lote", id_categoria=self.categoria, condicion="nueva",
            precio_venta=Decimal("50.00"), stock_actual=5,
        )
        self.vend_api.post(
            "/api/ventas/",
            self.payload_venta(detalles=[{"id_pieza": sin_lote.pk, "cantidad": 1}]),
            format="json",
        )
        r = self.admin_api.get("/api/reportes/").data["resumen"]
        self.assertEqual(r["piezas_sin_costo"], 1)
        self.assertEqual(Decimal(r["ingresos_sin_costo"]), Decimal("50.00"))
        self.assertEqual(r["margen"], 40.0)

    def test_desgloses(self):
        datos = self.admin_api.get("/api/reportes/").data
        metodos = {m["metodo"]: Decimal(m["ingresos"]) for m in datos["por_metodo_pago"]}
        self.assertEqual(metodos, {"efectivo": Decimal("300.00"), "transferencia": Decimal("200.00")})
        self.assertEqual(datos["por_vendedor"][0]["id_usuario"], self.vendedor.pk)
        self.assertEqual(datos["top_piezas"][0]["unidades"], 5)
        self.assertEqual(datos["top_clientes"][0]["compras"], 2)
        self.assertEqual(datos["compras"]["unidades"], 10)
        self.assertEqual(len(datos["por_dia"]), 30)

    def test_inventario_valorizado(self):
        inv = self.admin_api.get("/api/reportes/").data["inventario"]
        # Stock: 10 iniciales + 10 del lote - 5 vendidas = 15
        self.assertEqual(inv["unidades"], 15)
        self.assertEqual(Decimal(inv["valor_venta"]), Decimal("1500.00"))
        self.assertEqual(Decimal(inv["valor_costo"]), Decimal("900.00"))

    def test_rango_sin_ventas(self):
        r = self.admin_api.get("/api/reportes/?desde=2020-01-01&hasta=2020-01-31").data
        self.assertEqual(r["resumen"]["ventas"], 0)
        self.assertIsNone(r["resumen"]["margen"])
        self.assertEqual(len(r["por_dia"]), 31)

    def test_rango_invalido(self):
        for query in ("desde=2026-13-01", "desde=2026-05-10&hasta=2026-05-01",
                      "desde=2020-01-01&hasta=2026-01-01"):
            self.assertEqual(self.admin_api.get(f"/api/reportes/?{query}").status_code, 400, query)


# ---------------------------------------------------------------------------
# Integración entre sedes (contrato en CONTRATO-INTEGRACION.md)
# ---------------------------------------------------------------------------

CAMPOS_FACTURA = ["tipo", "numero", "fecha", "tercero", "subtotal", "iva", "total"]


class IntegracionBase(BaseAPITest):
    """Un lote de compra, una venta con cédula, una sin cédula y una anulada."""

    def setUp(self):
        super().setUp()
        self.proveedor.nit = "900123456-7"
        self.proveedor.save()
        self.admin_api.post(
            "/api/lotes/",
            {"id_pieza": self.pieza.pk, "id_proveedor": self.proveedor.pk,
             "cantidad": 5, "costo_unitario": "59.50"},
            format="json",
        )
        self.cliente.documento = "1098000001"
        self.cliente.save()
        self.sin_doc = Cliente.objects.create(nombres="Sin", apellidos="Cedula")
        self.venta = self.vend_api.post("/api/ventas/", self.payload_venta(cantidad=2), format="json").data
        self.vend_api.post("/api/ventas/", self.payload_venta(id_cliente=self.sin_doc.pk), format="json")
        anulada = self.vend_api.post("/api/ventas/", self.payload_venta(), format="json").data
        self.admin_api.post(f"/api/ventas/{anulada['id_venta']}/anular/")

    def token_integracion(self, correo="admin@tienda.com", clave=CLAVE):
        return self.anon.post("/api/login", {"correo": correo, "clave": clave}, format="json")

    def api_con_token(self, token):
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return api


class LoginSedesTests(IntegracionBase):

    def test_admin_recibe_token_en_el_formato_acordado(self):
        r = self.token_integracion(correo="ADMIN@tienda.com")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(list(r.data), ["token", "tipo", "expira_en", "usuario"])
        self.assertEqual(r.data["tipo"], "Bearer")
        self.assertEqual(r.data["expira_en"], 8 * 3600)
        self.assertEqual(r.data["usuario"]["rol"], "administrador")

    def test_errores_en_el_formato_acordado(self):
        casos = [
            ({"correo": "admin@tienda.com"}, 400),
            ({"correo": "admin@tienda.com", "clave": "mala"}, 401),
            ({"correo": "nadie@tienda.com", "clave": CLAVE}, 401),
            ({"correo": "vendedor@tienda.com", "clave": CLAVE}, 403),
            ({"correo": "cliente@mail.com", "clave": CLAVE}, 403),
        ]
        for cuerpo, codigo in casos:
            r = self.anon.post("/api/login", cuerpo, format="json")
            self.assertEqual(r.status_code, codigo, cuerpo)
            self.assertIn("error", r.data, cuerpo)

    def test_acepta_la_ruta_con_barra(self):
        r = self.anon.post("/api/login/", {"correo": "admin@tienda.com", "clave": CLAVE}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_token_de_integracion_no_administra_la_tienda(self):
        """El token dura horas: solo debe servir para leer facturas."""
        api = self.api_con_token(self.token_integracion().data["token"])
        self.assertEqual(api.get("/api/facturas").status_code, 200)
        self.assertEqual(api.get("/api/ventas/").status_code, 401)
        self.assertEqual(api.delete(f"/api/piezas/{self.pieza.pk}/").status_code, 401)
        self.assertEqual(api.post(f"/api/ventas/{self.venta['id_venta']}/anular/").status_code, 401)


class FacturasSedesTests(IntegracionBase):

    def setUp(self):
        super().setUp()
        self.api = self.api_con_token(self.token_integracion().data["token"])

    def test_estructura_igual_a_la_de_repuauto(self):
        d = self.api.get("/api/facturas").data
        self.assertEqual(
            list(d), ["sucursal", "desde", "hasta", "moneda", "iva_porcentaje", "resumen", "facturas"]
        )
        self.assertEqual(d["moneda"], "COP")
        self.assertEqual(d["iva_porcentaje"], 19)
        for f in d["facturas"]:
            self.assertEqual(list(f), CAMPOS_FACTURA)
            self.assertEqual(list(f["tercero"]), ["documento", "nombre"])
            self.assertRegex(f["numero"], r"^[VC]-\d{6}$")
            self.assertRegex(f["fecha"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-05:00$")
            self.assertRegex(f["total"], r"^\d+\.\d{2}$")
            self.assertEqual(Decimal(f["subtotal"]) + Decimal(f["iva"]), Decimal(f["total"]))

    def test_solo_ventas_activas_y_todas_las_compras(self):
        r = self.api.get("/api/facturas").data["resumen"]
        self.assertEqual(r["venta"]["cantidad"], 2)
        self.assertEqual(Decimal(r["venta"]["total"]), Decimal("300.00"))
        self.assertEqual(r["compra"]["cantidad"], 1)
        self.assertEqual(Decimal(r["compra"]["total"]), Decimal("297.50"))

    def test_iva_incluido(self):
        compra = [f for f in self.api.get("/api/facturas").data["facturas"] if f["tipo"] == "compra"][0]
        self.assertEqual(compra["subtotal"], "250.00")
        self.assertEqual(compra["iva"], "47.50")
        self.assertEqual(compra["tercero"], {"documento": "900123456-7", "nombre": "Mayorista"})

    def test_tercero_de_las_ventas(self):
        ventas = self.api.get("/api/facturas?tipo=venta").data["facturas"]
        documentos = {f["tercero"]["documento"] for f in ventas}
        self.assertEqual(documentos, {"1098000001", "222222222222"})
        self.assertEqual(ventas[0]["numero"], f"V-{self.venta['id_venta']:06d}")

    def test_filtro_por_tipo(self):
        d = self.api.get("/api/facturas?tipo=compra").data
        self.assertEqual(list(d["resumen"]), ["compra"])
        self.assertTrue(all(f["tipo"] == "compra" for f in d["facturas"]))

    def test_rango_sin_facturas(self):
        d = self.api.get("/api/facturas?desde=2020-01-01&hasta=2020-01-31").data
        self.assertEqual(d["facturas"], [])
        self.assertEqual(
            d["resumen"]["venta"], {"cantidad": 0, "subtotal": "0.00", "iva": "0.00", "total": "0.00"}
        )

    def test_errores(self):
        for query in ("tipo=otro", "desde=2026-13-01", "desde=2026-05-10&hasta=2026-05-01"):
            r = self.api.get(f"/api/facturas?{query}")
            self.assertEqual(r.status_code, 400, query)
            self.assertIn("error", r.data)
        r = self.anon.get("/api/facturas")
        self.assertEqual(r.status_code, 401)
        self.assertIn("error", r.data)

    def test_token_normal_del_administrador_tambien_sirve(self):
        self.assertEqual(self.admin_api.get("/api/facturas").status_code, 200)
        r = self.vend_api.get("/api/facturas")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data, {"error": "Solo un administrador puede usar la API."})


class ProveedorNitTests(BaseAPITest):

    def test_nit_vacio_se_guarda_como_nulo_y_no_choca(self):
        for nombre in ("A", "B"):
            r = self.admin_api.post("/api/proveedores/", {"nombre": nombre, "nit": " "}, format="json")
            self.assertEqual(r.status_code, 201)
            self.assertIsNone(r.data["nit"])

    def test_nit_invalido_o_repetido(self):
        r = self.admin_api.post("/api/proveedores/", {"nombre": "X", "nit": "ABC"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.admin_api.post("/api/proveedores/", {"nombre": "Y", "nit": "900111222-3"}, format="json")
        r = self.admin_api.post("/api/proveedores/", {"nombre": "Z", "nit": "900111222-3"}, format="json")
        self.assertEqual(r.status_code, 400)


# Respuesta de ejemplo de la documentación de RepuAuto (docs/API.md de su repositorio).
FACTURAS_REPUAUTO = {
    "sucursal": "Bucaramanga",
    "desde": "2026-10-01",
    "hasta": "2026-10-31",
    "moneda": "COP",
    "iva_porcentaje": 19,
    "resumen": {},
    "facturas": [
        {"tipo": "compra", "numero": "C-000045", "fecha": "2026-10-04T09:30:00-05:00",
         "tercero": {"documento": "900123456-7", "nombre": "Autopartes del Oriente S.A.S."},
         "subtotal": "567226.89", "iva": "107773.11", "total": "675000.00"},
        {"tipo": "venta", "numero": "V-000123", "fecha": "2026-10-30T10:15:00-05:00",
         "tercero": {"documento": "1098000001", "nombre": "Carlos Andrés Rueda Pinzón"},
         "subtotal": "100000.00", "iva": "19000.00", "total": "119000.00"},
    ],
}

REPUAUTO_PRUEBA = {"URL": "http://repuauto.test/api", "CORREO": "integracion@repuauto.com",
                   "CLAVE": "clave", "TIMEOUT": 2}


def respuesta_falsa(codigo, datos):
    r = mock.Mock(status_code=codigo)
    r.json.return_value = datos
    return r


def api_repuauto(facturas=FACTURAS_REPUAUTO, codigo_facturas=200):
    """Simula la API de RepuAuto: login devuelve un token y facturas el JSON dado."""
    def responder(metodo, url, **kwargs):
        if url.endswith("/login"):
            return respuesta_falsa(200, {"token": "tok", "tipo": "Bearer", "expira_en": 28800})
        return respuesta_falsa(codigo_facturas, facturas)
    return mock.patch("inventario.integraciones.repuauto.requests.request", side_effect=responder)


class ConsolidadoTests(IntegracionBase):

    URL = "/api/consolidado/?desde=2020-01-01&hasta=2030-12-31"

    def test_solo_administrador(self):
        self.assertEqual(self.vend_api.get(self.URL).status_code, 403)
        self.assertEqual(self.cli_api.get(self.URL).status_code, 403)
        self.assertEqual(self.anon.get(self.URL).status_code, 401)

    @override_settings(REPUAUTO={"URL": "", "CORREO": "", "CLAVE": "", "TIMEOUT": 2})
    def test_sin_configurar_muestra_solo_esta_sede(self):
        d = self.admin_api.get(self.URL).data
        self.assertEqual([s["estado"] for s in d["sedes"]], ["ok", "sin_configurar"])
        self.assertEqual(d["total"]["venta"]["cantidad"], 2)

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_junta_las_dos_sedes(self):
        with api_repuauto() as falso:
            d = self.admin_api.get(self.URL).data
            self.admin_api.get(self.URL)
        self.assertEqual([s["estado"] for s in d["sedes"]], ["ok", "ok"])
        self.assertEqual(d["sedes"][1]["sucursal"], "Bucaramanga")
        self.assertEqual(d["total"]["venta"]["cantidad"], 3)
        self.assertEqual(Decimal(d["total"]["venta"]["total"]), Decimal("119300.00"))
        self.assertEqual(Decimal(d["total"]["compra"]["total"]), Decimal("675297.50"))
        self.assertEqual({f["sucursal"] for f in d["facturas"]}, {"PC Stock", "Bucaramanga"})
        # El token se guarda: dos consultas, un solo inicio de sesión.
        logins = [c for c in falso.call_args_list if c.args[1].endswith("/login")]
        self.assertEqual(len(logins), 1)
        cabeceras = falso.call_args_list[-1].kwargs["headers"]
        self.assertEqual(cabeceras["Authorization"], "Bearer tok")
        # Salta la página de aviso de ngrok gratis (si no, llega HTML en vez de JSON).
        self.assertEqual(cabeceras["ngrok-skip-browser-warning"], "1")

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_otra_sede_caida_no_tumba_el_consolidado(self):
        with mock.patch("inventario.integraciones.repuauto.requests.request",
                        side_effect=requests.ConnectionError):
            r = self.admin_api.get(self.URL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["sedes"][1]["estado"], "error")
        self.assertIn("No se pudo conectar", r.data["sedes"][1]["error"])
        self.assertEqual(r.data["total"]["venta"]["cantidad"], 2)

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_renueva_el_token_vencido_una_vez(self):
        respuestas = iter([
            respuesta_falsa(200, {"token": "viejo", "expira_en": 28800}),
            respuesta_falsa(401, {"error": "El token venció."}),
            respuesta_falsa(200, {"token": "nuevo", "expira_en": 28800}),
            respuesta_falsa(200, FACTURAS_REPUAUTO),
        ])
        with mock.patch("inventario.integraciones.repuauto.requests.request",
                        side_effect=lambda *a, **k: next(respuestas)):
            d = self.admin_api.get(self.URL).data
        self.assertEqual(d["sedes"][1]["estado"], "ok")

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_respuesta_con_formato_distinto(self):
        with api_repuauto(facturas={"datos": []}):
            d = self.admin_api.get(self.URL).data
        self.assertEqual(d["sedes"][1]["estado"], "error")
        self.assertIn("formato acordado", d["sedes"][1]["error"])

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_ignora_facturas_ilegibles_de_la_otra_sede(self):
        malas = {**FACTURAS_REPUAUTO, "facturas": FACTURAS_REPUAUTO["facturas"] + [
            {"tipo": "venta", "numero": "V-9", "total": "mucho", "subtotal": "x", "iva": "y"},
            {"tipo": "devolucion", "numero": "D-1", "total": "1.00", "subtotal": "1.00", "iva": "0.00"},
        ]}
        with api_repuauto(facturas=malas):
            d = self.admin_api.get(self.URL).data
        self.assertEqual(d["sedes"][1]["resumen"]["venta"]["cantidad"], 1)


# ---------------------------------------------------------------------------
# Inventario entre sedes (formato de la sección 3 del docs/API.md de RepuAuto)
# ---------------------------------------------------------------------------

CAMPOS_PRODUCTO = ["codigo", "nombre", "categoria", "marca", "stock", "stock_minimo",
                   "precio_venta", "valor", "estado"]


class InventarioSedesTests(IntegracionBase):
    """Stock de la base: Ryzen 5 = 10 + 5 del lote - 3 vendidas = 12 (la anulada se devolvió)."""

    def setUp(self):
        super().setUp()
        self.api = self.api_con_token(self.token_integracion().data["token"])
        # update() y no save(): el objeto en memoria tiene el stock de antes de las ventas.
        Pieza.objects.filter(pk=self.pieza.pk).update(marca="AMD")
        gpu = CategoriaPieza.objects.create(nombre="GPU")
        self.bajo = Pieza.objects.create(nombre="RTX 4060", id_categoria=gpu, condicion="nueva",
                                         precio_venta=Decimal("1200.00"), stock_actual=3)
        self.justo = Pieza.objects.create(nombre="RX 6700", id_categoria=gpu, condicion="nueva",
                                          precio_venta=Decimal("900.00"), stock_actual=4)
        self.agotada = Pieza.objects.create(nombre="Arc A770", id_categoria=gpu, condicion="nueva",
                                            precio_venta=Decimal("800.00"), stock_actual=0)

    def productos(self, query=""):
        return {p["nombre"]: p for p in self.api.get(f"/api/inventario{query}").data["productos"]}

    def test_estructura_igual_a_la_de_repuauto(self):
        d = self.api.get("/api/inventario").data
        self.assertEqual(list(d), ["sucursal", "fecha", "moneda", "resumen", "productos"])
        self.assertEqual(list(d["resumen"]),
                         ["productos", "unidades", "valor", "en_stock", "stock_bajo", "agotado"])
        self.assertRegex(d["fecha"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-05:00$")
        for p in d["productos"]:
            self.assertEqual(list(p), CAMPOS_PRODUCTO)
            self.assertRegex(p["codigo"], r"^PZ-\d{6}$")
            self.assertRegex(p["valor"], r"^\d+\.\d{2}$")
            self.assertEqual(Decimal(p["valor"]), Decimal(p["precio_venta"]) * p["stock"])

    def test_estado_con_la_regla_de_repuauto(self):
        p = self.productos()
        self.assertEqual(p["Ryzen 5"]["stock"], 12)
        self.assertEqual(p["Ryzen 5"]["estado"], "en_stock")
        # Mínimo 4 para todas: 3 unidades es stock bajo, 4 ya no (igual que en las pantallas).
        self.assertEqual(p["RTX 4060"]["estado"], "stock_bajo")
        self.assertEqual(p["RX 6700"]["estado"], "en_stock")
        self.assertEqual(p["Arc A770"]["estado"], "agotado")
        self.assertTrue(all(x["stock_minimo"] == 4 for x in p.values()))

    def test_marca_y_orden(self):
        d = self.api.get("/api/inventario").data["productos"]
        self.assertEqual([(x["categoria"], x["nombre"]) for x in d],
                         sorted((x["categoria"], x["nombre"]) for x in d))
        p = {x["nombre"]: x for x in d}
        self.assertEqual(p["Ryzen 5"]["marca"], "AMD")
        self.assertEqual(p["RTX 4060"]["marca"], "Sin marca")

    def test_resumen_de_todo_aunque_se_filtre(self):
        todo = self.api.get("/api/inventario").data
        filtrado = self.api.get("/api/inventario?estado=stock_bajo").data
        self.assertEqual(filtrado["resumen"], todo["resumen"])
        self.assertEqual([p["nombre"] for p in filtrado["productos"]], ["RTX 4060"])
        r = todo["resumen"]
        self.assertEqual((r["productos"], r["unidades"]), (4, 12 + 3 + 4))
        self.assertEqual((r["en_stock"], r["stock_bajo"], r["agotado"]), (2, 1, 1))
        self.assertEqual(Decimal(r["valor"]), Decimal("1200.00") + Decimal("3600.00") + Decimal("3600.00"))

    def test_errores_y_permisos(self):
        r = self.api.get("/api/inventario?estado=otro")
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.data)
        self.assertEqual(self.anon.get("/api/inventario").status_code, 401)
        self.assertEqual(self.vend_api.get("/api/inventario").data,
                         {"error": "Solo un administrador puede usar la API."})
        self.assertEqual(self.api.get("/api/inventario/").status_code, 200)
        self.assertEqual(self.admin_api.get("/api/inventario").status_code, 200)


INVENTARIO_REPUAUTO = {
    "sucursal": "Bucaramanga",
    "fecha": "2026-11-10T11:45:00-05:00",
    "moneda": "COP",
    "resumen": {"productos": 2, "unidades": 13, "valor": "2105000.00",
                "en_stock": 1, "stock_bajo": 1, "agotado": 0},
    "productos": [
        {"codigo": "FRE-DIS-011", "nombre": "Disco de freno ventilado", "categoria": "Frenos",
         "marca": "Genérica", "stock": 1, "stock_minimo": 4, "precio_venta": "185000.00",
         "valor": "185000.00", "estado": "stock_bajo"},
        {"codigo": "FIL-ACE-001", "nombre": "Filtro de aceite", "categoria": "Filtros",
         "marca": "Bosch", "stock": 12, "stock_minimo": 3, "precio_venta": "160000.00",
         "valor": "1920000.00", "estado": "en_stock"},
    ],
}


class ConsolidadoInventarioTests(IntegracionBase):

    URL = "/api/consolidado/inventario/"

    def test_solo_administrador(self):
        self.assertEqual(self.vend_api.get(self.URL).status_code, 403)
        self.assertEqual(self.anon.get(self.URL).status_code, 401)

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_junta_el_inventario_de_las_dos_sedes(self):
        with api_repuauto(facturas=INVENTARIO_REPUAUTO):
            d = self.admin_api.get(self.URL).data
        self.assertEqual([s["estado"] for s in d["sedes"]], ["ok", "ok"])
        aliada = d["sedes"][1]
        self.assertEqual((aliada["sucursal"], aliada["resumen"]["productos"]), ("Bucaramanga", 2))
        self.assertEqual(d["total"]["productos"], 3)
        self.assertEqual(d["total"]["unidades"], 12 + 13)
        self.assertEqual({p["sucursal"] for p in d["productos"]}, {"PC Stock", "Bucaramanga"})

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_sede_que_no_publica_inventario(self):
        with api_repuauto(facturas={"error": "La ruta no existe."}, codigo_facturas=404):
            d = self.admin_api.get(self.URL).data
        self.assertEqual(d["sedes"][1]["estado"], "error")
        self.assertIn("todavía no publica /api/inventario", d["sedes"][1]["error"])
        self.assertEqual(d["total"]["productos"], 1)

    @override_settings(REPUAUTO=REPUAUTO_PRUEBA)
    def test_ignora_productos_ilegibles(self):
        malos = {**INVENTARIO_REPUAUTO, "productos": INVENTARIO_REPUAUTO["productos"] + [
            {"nombre": "Sin estado", "stock": 1, "precio_venta": "1.00", "valor": "1.00"},
            {"nombre": "Stock raro", "stock": "mucho", "precio_venta": "1.00", "valor": "1.00", "estado": "en_stock"},
        ]}
        with api_repuauto(facturas=malos):
            d = self.admin_api.get(self.URL).data
        self.assertEqual(d["sedes"][1]["resumen"]["productos"], 2)

    @override_settings(REPUAUTO={"URL": "", "CORREO": "", "CLAVE": "", "TIMEOUT": 2})
    def test_sin_configurar(self):
        d = self.admin_api.get(self.URL).data
        self.assertEqual(d["sedes"][1]["estado"], "sin_configurar")
        self.assertEqual(d["total"]["productos"], 1)
