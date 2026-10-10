from datetime import timedelta
from decimal import Decimal
import random

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils import timezone

from inventario.models import (
    CategoriaPieza,
    Cliente,
    DetalleVenta,
    LoteCompra,
    Pieza,
    Proveedor,
    Usuario,
    Venta,
)

print("\n--- Iniciando poblado de datos de prueba ---\n")

with transaction.atomic():
    ahora = timezone.now()

    # =========================================================================
    # 1. CATEGORÍAS (6 categorías de hardware de PC)
    # =========================================================================
    nombres_categorias = [
        "Procesadores (CPU)",
        "Tarjetas Gráficas (GPU)",
        "Memorias RAM",
        "Almacenamiento (SSD/HDD)",
        "Motherboards",
        "Fuentes de Poder (PSU)",
    ]

    categorias_dict = {}
    for nombre in nombres_categorias:
        cat = CategoriaPieza.objects.create(nombre=nombre)
        categorias_dict[nombre] = cat

    print(f"✔ {len(categorias_dict)} Categorías creadas.")

    # =========================================================================
    # 2. PROVEEDORES (5 empresas mayoristas realistas)
    # =========================================================================
    proveedores_data = [
        {
            "nombre": "TechDistribuciones Mayorista S.A.S.",
            "telefono": "3104567890",
            "contacto": "Alvaro Mendoza - Gerente Comercial",
        },
        {
            "nombre": "Global Chipset & Hardware Latam",
            "telefono": "3158901234",
            "contacto": "Paola Andrea Silva - Ventas Corporativas",
        },
        {
            "nombre": "Andes Componentes del Norte",
            "telefono": "3012345678",
            "contacto": "Rodrigo Cárdenas - Representante de Marca",
        },
        {
            "nombre": "Silicio Express Importaciones",
            "telefono": "3207890123",
            "contacto": "Mónica Tatiana Duarte - Logística y Ventas",
        },
        {
            "nombre": "PC Master Wholesale Distributors",
            "telefono": "3186543210",
            "contacto": "Fabián Leonardo Gómez - Cuentas Clave",
        },
    ]

    proveedores = [Proveedor.objects.create(**p) for p in proveedores_data]
    print(f"✔ {len(proveedores)} Proveedores creados.")

    # =========================================================================
    # 3. PIEZAS (23 piezas variadas: nuevas y reacondicionadas con stock inicial)
    # =========================================================================
    piezas_data = [
        # Procesadores
        {
            "nombre": "AMD Ryzen 5 5600X (6C/12T, hasta 4.6GHz)",
            "cat": "Procesadores (CPU)",
            "condicion": "nueva",
            "precio_venta": Decimal("155.00"),
            "descripcion": "Procesador socket AM4, 32MB L3 Cache, TDP 65W, incluye Wraith Stealth.",
            "stock": 14,
        },
        {
            "nombre": "AMD Ryzen 7 7800X3D (8C/16T, 3D V-Cache)",
            "cat": "Procesadores (CPU)",
            "condicion": "nueva",
            "precio_venta": Decimal("389.00"),
            "descripcion": "Socket AM5, el procesador definitivo para gaming con 96MB 3D V-Cache.",
            "stock": 8,
        },
        {
            "nombre": "Intel Core i5-12400F (6C/12T, hasta 4.4GHz)",
            "cat": "Procesadores (CPU)",
            "condicion": "nueva",
            "precio_venta": Decimal("130.00"),
            "descripcion": "Socket LGA1700, excelente relación calidad/precio para gaming y trabajo.",
            "stock": 16,
        },
        {
            "nombre": "Intel Core i7-13700K (16C/24T, hasta 5.4GHz)",
            "cat": "Procesadores (CPU)",
            "condicion": "reacondicionada",
            "precio_venta": Decimal("295.00"),
            "descripcion": "Unidad certificada grado A, probado en banco de estrés, pasta térmica nueva.",
            "stock": 6,
        },
        # Tarjetas Gráficas
        {
            "nombre": "NVIDIA GeForce RTX 4060 8GB GDDR6 (MSI Ventus 2X)",
            "cat": "Tarjetas Gráficas (GPU)",
            "condicion": "nueva",
            "precio_venta": Decimal("299.00"),
            "descripcion": "Arquitectura Ada Lovelace, soporte DLSS 3 y Ray Tracing de última gen.",
            "stock": 10,
        },
        {
            "nombre": "NVIDIA GeForce RTX 3070 8GB GDDR6 (ASUS TUF)",
            "cat": "Tarjetas Gráficas (GPU)",
            "condicion": "reacondicionada",
            "precio_venta": Decimal("275.00"),
            "descripcion": "Mantenimiento completo: thermal pads cambiados, disipación al 100%.",
            "stock": 7,
        },
        {
            "nombre": "AMD Radeon RX 6700 XT 12GB (Sapphire Pulse)",
            "cat": "Tarjetas Gráficas (GPU)",
            "condicion": "reacondicionada",
            "precio_venta": Decimal("245.00"),
            "descripcion": "Reacondicionada en fábrica, 12GB VRAM ideal para 1440p, impecable estado.",
            "stock": 5,
        },
        {
            "nombre": "NVIDIA GeForce RTX 4070 SUPER 12GB (Gigabyte Windforce)",
            "cat": "Tarjetas Gráficas (GPU)",
            "condicion": "nueva",
            "precio_venta": Decimal("599.00"),
            "descripcion": "Alto rendimiento para 1440p Ultra y 4K con Ray Tracing activado.",
            "stock": 6,
        },
        # Memorias RAM
        {
            "nombre": "Corsair Vengeance LPX 16GB (2x8GB) DDR4 3200MHz CL16",
            "cat": "Memorias RAM",
            "condicion": "nueva",
            "precio_venta": Decimal("44.00"),
            "descripcion": "Kit dual channel, disipador de aluminio anodizado de bajo perfil.",
            "stock": 24,
        },
        {
            "nombre": "Kingston FURY Beast 32GB (2x16GB) DDR4 3200MHz CL16",
            "cat": "Memorias RAM",
            "condicion": "nueva",
            "precio_venta": Decimal("72.00"),
            "descripcion": "Kit de alto rendimiento compatible con perfiles Intel XMP y AMD Ryzen.",
            "stock": 15,
        },
        {
            "nombre": "G.Skill Ripjaws S5 32GB (2x16GB) DDR5 6000MHz CL36",
            "cat": "Memorias RAM",
            "condicion": "nueva",
            "precio_venta": Decimal("112.00"),
            "descripcion": "Memoria DDR5 de alta velocidad con disipador negro mate para chipsets modernos.",
            "stock": 12,
        },
        {
            "nombre": "Crucial 16GB (1x16GB) DDR4 2666MHz",
            "cat": "Memorias RAM",
            "condicion": "reacondicionada",
            "precio_venta": Decimal("26.00"),
            "descripcion": "Módulo OEM verificado con MemTest86 sin errores, ideal para actualización.",
            "stock": 9,
        },
        # Almacenamiento
        {
            "nombre": "Kingston NV2 1TB M.2 2280 NVMe PCIe 4.0",
            "cat": "Almacenamiento (SSD/HDD)",
            "condicion": "nueva",
            "precio_venta": Decimal("60.00"),
            "descripcion": "Lectura hasta 3500MB/s, ideal para arranque rápido y almacenamiento principal.",
            "stock": 20,
        },
        {
            "nombre": "Samsung 980 PRO 2TB M.2 NVMe PCIe 4.0 con Disipador",
            "cat": "Almacenamiento (SSD/HDD)",
            "condicion": "nueva",
            "precio_venta": Decimal("165.00"),
            "descripcion": "Velocidades secuenciales de hasta 7000MB/s, compatible con PS5 y PC Master Race.",
            "stock": 9,
        },
        {
            "nombre": "Crucial BX500 480GB SATA 2.5''",
            "cat": "Almacenamiento (SSD/HDD)",
            "condicion": "nueva",
            "precio_venta": Decimal("34.00"),
            "descripcion": "SSD SATA tradicional para repotenciar portátiles o PCs de oficina.",
            "stock": 18,
        },
        {
            "nombre": "Western Digital Blue 1TB HDD 3.5'' 7200 RPM",
            "cat": "Almacenamiento (SSD/HDD)",
            "condicion": "reacondicionada",
            "precio_venta": Decimal("22.00"),
            "descripcion": "Disco mecánico testeado con CrystalDiskInfo al 100% de salud, cero sectores dañados.",
            "stock": 11,
        },
        # Motherboards
        {
            "nombre": "ASUS TUF Gaming B550-PLUS WiFi II (Socket AM4)",
            "cat": "Motherboards",
            "condicion": "nueva",
            "precio_venta": Decimal("145.00"),
            "descripcion": "Placa base ATX, PCIe 4.0, doble M.2, WiFi 6 integrado, VRM robusto.",
            "stock": 8,
        },
        {
            "nombre": "MSI B650 Gaming Plus WiFi (Socket AM5)",
            "cat": "Motherboards",
            "condicion": "nueva",
            "precio_venta": Decimal("179.00"),
            "descripcion": "Soporta procesadores serie AMD Ryzen 7000 y 8000, DDR5, conectividad 2.5G LAN.",
            "stock": 10,
        },
        {
            "nombre": "Gigabyte B760M DS3H AX DDR4 (LGA1700)",
            "cat": "Motherboards",
            "condicion": "nueva",
            "precio_venta": Decimal("115.00"),
            "descripcion": "Formato micro-ATX para procesadores Intel de 12va, 13ra y 14ta generación.",
            "stock": 9,
        },
        {
            "nombre": "ASUS ROG Strix Z690-F Gaming WiFi (LGA1700)",
            "cat": "Motherboards",
            "condicion": "reacondicionada",
            "precio_venta": Decimal("195.00"),
            "descripcion": "Gama alta, BIOS actualizada, accesorios completos, excelente para overclocking.",
            "stock": 4,
        },
        # Fuentes de Poder
        {
            "nombre": "Corsair RM750e 750W 80 Plus Gold Modular",
            "cat": "Fuentes de Poder (PSU)",
            "condicion": "nueva",
            "precio_venta": Decimal("108.00"),
            "descripcion": "Certificación Cybenetics Gold, compatibilidad con ATX 3.0 y cable PCIe 5.0 12VHPWR.",
            "stock": 11,
        },
        {
            "nombre": "EVGA 600 W1 600W 80 Plus White",
            "cat": "Fuentes de Poder (PSU)",
            "condicion": "reacondicionada",
            "precio_venta": Decimal("38.00"),
            "descripcion": "Fuente económica de 600W inspeccionada y certificada para ensambles básicos.",
            "stock": 8,
        },
        {
            "nombre": "Seasonic FOCUS GX-850 850W 80 Plus Gold Full Modular",
            "cat": "Fuentes de Poder (PSU)",
            "condicion": "nueva",
            "precio_venta": Decimal("142.00"),
            "descripcion": "Condensadores 100% japoneses, modo híbrido de ventilador silencioso, 10 años garantía.",
            "stock": 7,
        },
    ]

    piezas = []
    for item in piezas_data:
        p = Pieza.objects.create(
            nombre=item["nombre"],
            id_categoria=categorias_dict[item["cat"]],
            condicion=item["condicion"],
            precio_venta=item["precio_venta"],
            descripcion=item["descripcion"],
            stock_actual=item["stock"],
        )
        piezas.append(p)

    print(f"✔ {len(piezas)} Piezas creadas con su stock inicial.")

    # =========================================================================
    # 4. USUARIOS DEL SISTEMA (4 usuarios: 2 administradores y 2 vendedores)
    # =========================================================================
    usuarios_data = [
        {
            "nombres": "Carlos Andrés",
            "apellidos": "Mendoza Riaño",
            "documento": "1098765432",
            "telefono": "3112233445",
            "email": "carlos.admin@techparts.com",
            "rol": "administrador",
            "fecha_registro": ahora - timedelta(days=120),
        },
        {
            "nombres": "Diana Patricia",
            "apellidos": "Ortiz Herrera",
            "documento": "1098765433",
            "telefono": "3123344556",
            "email": "diana.admin@techparts.com",
            "rol": "administrador",
            "fecha_registro": ahora - timedelta(days=100),
        },
        {
            "nombres": "Laura Marcela",
            "apellidos": "Gómez Quintero",
            "documento": "1098765434",
            "telefono": "3134455667",
            "email": "laura.ventas@techparts.com",
            "rol": "vendedor",
            "fecha_registro": ahora - timedelta(days=90),
        },
        {
            "nombres": "Juan Camilo",
            "apellidos": "Rincón Parra",
            "documento": "1098765435",
            "telefono": "3145566778",
            "email": "juan.ventas@techparts.com",
            "rol": "vendedor",
            "fecha_registro": ahora - timedelta(days=60),
        },
    ]

    usuarios = [Usuario.objects.create(**u) for u in usuarios_data]
    vendedores = [u for u in usuarios if u.rol == "vendedor"]
    print(f"✔ {len(usuarios)} Usuarios creados (administradores y vendedores).")

    # =========================================================================
    # 5. CLIENTES (9 clientes: 5 con cuenta hasheada y 4 sin registrar)
    # =========================================================================
    password_hasheada = make_password("cliente123")

    clientes_data = [
        # Clientes con cuenta registrada (login activo con password 'cliente123')
        {
            "nombres": "Andrés Felipe",
            "apellidos": "Silva Vega",
            "documento": "1094112233",
            "telefono": "3001112233",
            "email": "andres.silva@gmail.com",
            "password": password_hasheada,
            "fecha_registro": ahora - timedelta(days=70),
        },
        {
            "nombres": "Mariana",
            "apellidos": "Ruiz Peña",
            "documento": "1094223344",
            "telefono": "3002223344",
            "email": "mariana.ruiz@hotmail.com",
            "password": password_hasheada,
            "fecha_registro": ahora - timedelta(days=55),
        },
        {
            "nombres": "Diego Fernando",
            "apellidos": "Torres Celis",
            "documento": "1094334455",
            "telefono": "3003334455",
            "email": "diego.torres@outlook.com",
            "password": password_hasheada,
            "fecha_registro": ahora - timedelta(days=45),
        },
        {
            "nombres": "Valentina",
            "apellidos": "Morales Castro",
            "documento": "1094445566",
            "telefono": "3004445566",
            "email": "vale.morales@gmail.com",
            "password": password_hasheada,
            "fecha_registro": ahora - timedelta(days=35),
        },
        {
            "nombres": "Mateo Alejandro",
            "apellidos": "Vargas Nieto",
            "documento": "1094556677",
            "telefono": "3005556677",
            "email": "mateo.vargas@yahoo.com",
            "password": password_hasheada,
            "fecha_registro": ahora - timedelta(days=20),
        },
        # Clientes sin cuenta (compras directas en tienda física)
        {
            "nombres": "Camilo Ernesto",
            "apellidos": "Duarte Flórez",
            "documento": "1094667788",
            "telefono": "3006667788",
            "email": None,
            "password": None,
            "fecha_registro": None,
        },
        {
            "nombres": "Sofía Lucía",
            "apellidos": "Herrera Meza",
            "documento": "1094778899",
            "telefono": "3007778899",
            "email": None,
            "password": None,
            "fecha_registro": None,
        },
        {
            "nombres": "Daniel Esteban",
            "apellidos": "Pardo León",
            "documento": "1094889900",
            "telefono": "3008889900",
            "email": None,
            "password": None,
            "fecha_registro": None,
        },
        {
            "nombres": "Gabriela",
            "apellidos": "Restrepo Ríos",
            "documento": "1094990011",
            "telefono": "3009990011",
            "email": None,
            "password": None,
            "fecha_registro": None,
        },
    ]

    clientes = [Cliente.objects.create(**c) for c in clientes_data]
    print(f"✔ {len(clientes)} Clientes creados (5 con cuenta hasheada, 4 sin cuenta).")

    # =========================================================================
    # 6. LOTES DE COMPRA (13 lotes: compras a proveedores en los últimos 2-3 meses)
    # =========================================================================
    lotes_config = [
        # (index_pieza, index_proveedor, cantidad, margen_costo_aprox, dias_atras)
        (0, 0, 10, Decimal("115.00"), 80),  # Ryzen 5 5600X
        (1, 1, 5, Decimal("300.00"), 75),   # Ryzen 7 7800X3D
        (2, 2, 12, Decimal("98.00"), 70),   # i5-12400F
        (4, 0, 8, Decimal("230.00"), 65),   # RTX 4060
        (5, 3, 5, Decimal("210.00"), 60),   # RTX 3070 reacondicionada
        (7, 4, 4, Decimal("480.00"), 55),   # RTX 4070 SUPER
        (8, 1, 20, Decimal("32.00"), 50),   # RAM Corsair LPX
        (10, 2, 10, Decimal("85.00"), 45),  # RAM G.Skill DDR5
        (12, 0, 15, Decimal("42.00"), 40),  # SSD Kingston NV2
        (13, 4, 6, Decimal("125.00"), 35),  # SSD Samsung 980 Pro
        (16, 2, 6, Decimal("110.00"), 30),  # Asus TUF B550
        (17, 1, 8, Decimal("138.00"), 25),  # MSI B650
        (20, 3, 8, Decimal("80.00"), 20),   # PSU Corsair 750W
    ]

    lotes = []
    for p_idx, prov_idx, cant, costo, dias in lotes_config:
        lote = LoteCompra.objects.create(
            id_proveedor=proveedores[prov_idx],
            id_pieza=piezas[p_idx],
            cantidad=cant,
            costo_unitario=costo,
            fecha_compra=ahora - timedelta(days=dias),
        )
        lotes.append(lote)

    print(f"✔ {len(lotes)} Lotes de compra creados con costos inferiores al PVP.")

    # =========================================================================
    # 7. VENTAS Y DETALLES DE VENTA (8 ventas en el último mes)
    # Regla: descontar stock_actual de la pieza y calcular el total de la venta.
    # =========================================================================
    simulaciones_ventas = [
        # Venta 1: Cliente registrado, ensamble gama media (Ryzen 5600X + RAM LPX + B550)
        {
            "cliente_idx": 0,
            "vendedor_idx": 0,
            "metodo_pago": "transferencia",
            "dias_atras": 27,
            "items": [(0, 1), (8, 2), (16, 1)],  # (pieza_idx, cantidad)
        },
        # Venta 2: Cliente registrado, tarjeta gráfica RTX 4060
        {
            "cliente_idx": 1,
            "vendedor_idx": 1,
            "metodo_pago": "tarjeta_credito",
            "dias_atras": 24,
            "items": [(4, 1), (20, 1)],
        },
        # Venta 3: Cliente casual sin cuenta, actualización de almacenamiento
        {
            "cliente_idx": 5,
            "vendedor_idx": 0,
            "metodo_pago": "efectivo",
            "dias_atras": 20,
            "items": [(12, 2)],
        },
        # Venta 4: Cliente registrado, ensamble AM5 entusiasta (7800X3D + DDR5 + 4070 SUPER)
        {
            "cliente_idx": 2,
            "vendedor_idx": 1,
            "metodo_pago": "transferencia",
            "dias_atras": 16,
            "items": [(1, 1), (10, 1), (7, 1)],
        },
        # Venta 5: Cliente sin cuenta, disco duro reacondicionado + SSD SATA
        {
            "cliente_idx": 6,
            "vendedor_idx": 0,
            "metodo_pago": "efectivo",
            "dias_atras": 13,
            "items": [(14, 1), (15, 1)],
        },
        # Venta 6: Cliente registrado, upgrade Intel (i5-12400F + RAM Kingston + B760)
        {
            "cliente_idx": 3,
            "vendedor_idx": 1,
            "metodo_pago": "tarjeta_debito",
            "dias_atras": 9,
            "items": [(2, 1), (9, 1), (18, 1)],
        },
        # Venta 7: Cliente sin cuenta, tarjeta reacondicionada + fuente
        {
            "cliente_idx": 7,
            "vendedor_idx": 0,
            "metodo_pago": "tarjeta_debito",
            "dias_atras": 5,
            "items": [(6, 1), (21, 1)],
        },
        # Venta 8: Cliente registrado, SSD premium NVMe de 2TB
        {
            "cliente_idx": 4,
            "vendedor_idx": 1,
            "metodo_pago": "tarjeta_credito",
            "dias_atras": 2,
            "items": [(13, 1)],
        },
    ]

    ventas_creadas = []
    detalles_creados = 0

    for sim in simulaciones_ventas:
        cliente_obj = clientes[sim["cliente_idx"]]
        vendedor_obj = vendedores[sim["vendedor_idx"]]
        fecha_venta = ahora - timedelta(days=sim["dias_atras"])

        # Creamos la cabecera de la venta con total inicial 0
        venta = Venta.objects.create(
            id_cliente=cliente_obj,
            id_vendedor=vendedor_obj,
            fecha=fecha_venta,
            metodo_pago=sim["metodo_pago"],
            total=Decimal("0.00"),
        )

        total_venta = Decimal("0.00")

        for pieza_idx, cant_a_vender in sim["items"]:
            pieza_obj = piezas[pieza_idx]

            # Validación de seguridad de stock
            if pieza_obj.stock_actual < cant_a_vender:
                raise ValueError(
                    f"Stock insuficiente para {pieza_obj.nombre}: "
                    f"Disponible={pieza_obj.stock_actual}, Solicitado={cant_a_vender}"
                )

            # 1. Crear detalle de venta
            precio_unit = pieza_obj.precio_venta
            DetalleVenta.objects.create(
                id_venta=venta,
                id_pieza=pieza_obj,
                cantidad=cant_a_vender,
                precio_unitario=precio_unit,
            )
            detalles_creados += 1

            # 2. Descontar stock actual
            pieza_obj.stock_actual -= cant_a_vender
            pieza_obj.save()

            # 3. Acumular subtotal
            total_venta += Decimal(cant_a_vender) * precio_unit

        # Actualizar total de la venta
        venta.total = total_venta
        venta.save()
        ventas_creadas.append(venta)

    print(f"✔ {len(ventas_creadas)} Ventas y {detalles_creados} Detalles de venta creados con éxito.")

# =============================================================================
# RESUMEN FINAL
# =============================================================================
print("\n" + "=" * 55)
print("     RESUMEN DE REGISTROS EN BASE DE DATOS")
print("=" * 55)
print(f"  - Categorías creadas:        {CategoriaPieza.objects.count()}")
print(f"  - Proveedores creados:       {Proveedor.objects.count()}")
print(f"  - Piezas registradas:        {Pieza.objects.count()}")
print(f"  - Usuarios del sistema:      {Usuario.objects.count()}")
print(f"  - Clientes en base de datos: {Cliente.objects.count()}")
print(f"  - Lotes de compra:           {LoteCompra.objects.count()}")
print(f"  - Ventas completadas:        {Venta.objects.count()}")
print(f"  - Detalles de venta:         {DetalleVenta.objects.count()}")
print("=" * 55)
print("✔ Base de datos poblada de forma consistente.\n")