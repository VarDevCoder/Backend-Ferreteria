"""Siembra datos de ejemplo para una demo: empresa ficticia, un usuario por
rol, categorías, productos con stock inicial, clientes, proveedores con su
catálogo y un pedido avanzado en el flujo, para que la demo no arranque con
las pantallas vacías.

Solo corre si se pide explícitamente (variable SEED_DEMO=true o `--demo`).
Una empresa real NO usa este script: arranca con la base vacía y el primer
ingreso al sistema pide cargar los datos de la ferretería y crear el
usuario administrador.

Uso:
    python seed.py                   # no hace nada salvo que SEED_DEMO=true
    python seed.py --demo            # crea los datos demo si no existen (idempotente)
    python seed.py --demo --reset    # borra todo el esquema y lo vuelve a crear
"""
from __future__ import annotations

import sys

from sqlalchemy import text

from app.application.services.catalogo_service import CategoriaService, ProductoService
from app.application.services.contactos_service import ClienteService, ProveedorProductoService, ProveedorService
from app.application.services.orden_compra_service import OrdenCompraService
from app.application.services.pedido_cliente_service import PedidoClienteService
from app.application.services.solicitud_presupuesto_service import SolicitudPresupuestoService
from app.application.services.inventario_service import InventarioService
from app.core.config import get_settings
from app.core.tiempo import hoy
from app.domain.entities import Empresa, Usuario
from app.domain.enums import RolUsuario
from app.infrastructure.db.models import Base
from app.infrastructure.db.migraciones import aplicar_migraciones
from app.infrastructure.db.repositories.catalogo_repository import SqlAlchemyCategoriaRepository, SqlAlchemyProductoRepository
from app.infrastructure.db.repositories.contactos_repository import (
    SqlAlchemyClienteRepository,
    SqlAlchemyProveedorProductoRepository,
    SqlAlchemyProveedorRepository,
)
from app.infrastructure.db.repositories.flujo_repository import (
    SqlAlchemyCajaTurnoRepository,
    SqlAlchemyMovimientoInventarioRepository,
    SqlAlchemyOrdenCompraRepository,
    SqlAlchemyOrdenEnvioRepository,
    SqlAlchemyPedidoClienteRepository,
    SqlAlchemySolicitudPresupuestoRepository,
)
from app.application.services.cobro_pedido_service import CobroPedidoService
from app.application.services.cuenta_corriente_service import CuentaCorrienteService
from app.application.services.orden_envio_service import OrdenEnvioService
from app.infrastructure.db.demo_historial import (
    cargar_logistica,
    cargar_stock_no_vendible,
    completar_medios_de_pago,
    generar_historial,
)
from app.infrastructure.db.repositories.cobro_pedido_repository import SqlAlchemyPagoPedidoRepository
from app.infrastructure.db.repositories.cuenta_corriente_repository import SqlAlchemyCuentaCorrienteRepository
from app.infrastructure.db.repositories.empresa_repository import SqlAlchemyEmpresaRepository
from app.infrastructure.db.repositories.usuario_repository import SqlAlchemyUsuarioRepository
from app.infrastructure.db.session import SessionLocal, engine
from app.infrastructure.security.password_hasher import hash_password

DEMO_PASSWORD = "demo12345"
# email, nombre, rol. El primero es el admin con el que se presenta la demo.
USUARIOS_DEMO = [
    ("demo@sail.local", "Admin Demo", RolUsuario.ADMIN),
    ("encargado@sail.local", "Encargado Demo", RolUsuario.ENCARGADO),
    ("vendedor@sail.local", "Vendedor Demo", RolUsuario.VENDEDOR),
    ("deposito@sail.local", "Depósito Demo", RolUsuario.DEPOSITO),
]
# Usuarios demo de versiones anteriores (antes de llamarse SAIL). Se
# desactivan, no se borran: tienen ventas y movimientos a su nombre.
DOMINIOS_DEMO_ANTERIORES = ("@ankor.local", "@ferreteria.local")

CATEGORIAS_EXTRA = [
    ("Pinturería", "Pinturas, rodillos y accesorios", 4),
    ("Bulonería", "Tornillos, bulones, clavos y tarugos", 5),
    ("Construcción", "Materiales de obra", 6),
]
# nombre, categoría, precio de compra (Gs.), stock mínimo, unidad
PRODUCTOS_EXTRA = [
    ("Pintura látex interior blanco 20L", "Pinturería", 210000, 4, "balde"),
    ("Pintura látex exterior 4L", "Pinturería", 85000, 6, "lata"),
    ("Rodillo antigota 23cm", "Pinturería", 18000, 10, "pz"),
    ("Pincel 2\"", "Pinturería", 9000, 15, "pz"),
    ("Lija al agua N°120", "Pinturería", 2500, 50, "pz"),
    ("Silicona transparente 280ml", "Ferretería general", 14000, 12, "pz"),
    ("Clavos 2\" (kg)", "Bulonería", 12000, 10, "kg"),
    ("Bulón 1/4\" x 2\" con tuerca", "Bulonería", 800, 200, "pz"),
    ("Tarugo N°8 (bolsa 100)", "Bulonería", 9000, 10, "bolsa"),
    ("Destornillador Phillips PH2", "Ferretería general", 15000, 6, "pz"),
    ("Alicate universal 8\"", "Ferretería general", 38000, 5, "pz"),
    ("Cinta métrica 5m", "Ferretería general", 22000, 6, "pz"),
    ("Amoladora angular 4 1/2\" 850W", "Ferretería general", 320000, 2, "pz"),
    ("Disco de corte 4 1/2\"", "Ferretería general", 6000, 25, "pz"),
    ("Foco LED 12W", "Electricidad", 9500, 30, "pz"),
    ("Tomacorriente doble", "Electricidad", 12000, 15, "pz"),
    ("Codo PVC 1/2\"", "Plomería", 2500, 40, "pz"),
    ("Cemento portland 50kg", "Construcción", 62000, 20, "bolsa"),
]
CLIENTES_EXTRA = [
    {"nombre": "Juan Benítez", "ruc": "4567890-1", "telefono": "0971555111", "email": None, "direccion": "Barrio Obrero", "ciudad": "Asunción"},
    {"nombre": "Constructora Mbaretê S.R.L.", "ruc": "80055511-3", "telefono": "0981777222", "email": "obras@mbarete.com.py", "direccion": "Ruta Transchaco km 12", "ciudad": "Mariano Roque Alonso"},
    {"nombre": "Electricista Ramón Ortiz", "ruc": "3456789-0", "telefono": "0991444333", "email": None, "direccion": "Calle Palma 455", "ciudad": "Fernando de la Mora"},
]


def main(migrar: bool = True, forzar_demo: bool = False) -> None:
    if not (forzar_demo or "--demo" in sys.argv or get_settings().seed_demo):
        print("SEED_DEMO no está activo: no se cargan datos de ejemplo.")
        return

    if "--reset" in sys.argv:
        print("Recreando el esquema completo...")
        Base.metadata.drop_all(engine)
        with engine.begin() as conexion:
            conexion.execute(text("DROP TABLE IF EXISTS alembic_version"))
    # El esquema lo arman las migraciones (no `create_all`, que crearía las
    # tablas nuevas pero no las columnas nuevas de las tablas existentes).
    if migrar:
        aplicar_migraciones()

    db = SessionLocal()
    try:
        usuarios = SqlAlchemyUsuarioRepository(db)
        categorias_repo = SqlAlchemyCategoriaRepository(db)
        productos_repo = SqlAlchemyProductoRepository(db)
        clientes_repo = SqlAlchemyClienteRepository(db)
        proveedores_repo = SqlAlchemyProveedorRepository(db)
        catalogo_repo = SqlAlchemyProveedorProductoRepository(db)
        pedidos_repo = SqlAlchemyPedidoClienteRepository(db)
        solicitudes_repo = SqlAlchemySolicitudPresupuestoRepository(db)
        ordenes_compra_repo = SqlAlchemyOrdenCompraRepository(db)
        SqlAlchemyMovimientoInventarioRepository(db)  # solo para dejar la tabla creada/consistente

        categorias = CategoriaService(categorias_repo)
        productos = ProductoService(productos_repo)
        clientes = ClienteService(clientes_repo)
        proveedores = ProveedorService(proveedores_repo, usuarios)
        catalogo = ProveedorProductoService(catalogo_repo)
        pedidos = PedidoClienteService(pedidos_repo, clientes_repo, proveedores_repo, solicitudes_repo, productos_repo)
        solicitudes = SolicitudPresupuestoService(solicitudes_repo, proveedores_repo, pedidos_repo, ordenes_compra_repo)
        OrdenCompraService(ordenes_compra_repo, productos_repo, SqlAlchemyMovimientoInventarioRepository(db), pedidos_repo)

        empresa_repo = SqlAlchemyEmpresaRepository(db)
        if empresa_repo.get().nombre_comercial == Empresa().nombre_comercial:
            empresa_repo.save(Empresa(
                nombre_comercial="Ferretería Demo", razon_social="Ferretería Demo S.A.", ruc="80000000-0",
                direccion="Av. Principal 123", ciudad="Asunción", telefono="021 000 000",
            ))

        for email, nombre, rol in USUARIOS_DEMO:
            if usuarios.get_by_email(email) is None:
                usuarios.add(Usuario(id=None, name=nombre, email=email, password_hash=hash_password(DEMO_PASSWORD), rol=rol))
                print(f"Usuario demo {email} ({rol.value}) creado — contraseña: {DEMO_PASSWORD}")
        demo_user = usuarios.get_by_email(USUARIOS_DEMO[0][0])
        for anterior in usuarios.list_internos():
            if anterior.activo and anterior.email.endswith(DOMINIOS_DEMO_ANTERIORES):
                anterior.activo = False
                usuarios.update(anterior)
                print(f"Usuario demo anterior {anterior.email} desactivado")

        if not categorias_repo.list():
            cat_ferreteria = categorias.crear("Ferretería general", "Herramientas e insumos de ferretería", 1)
            cat_electricidad = categorias.crear("Electricidad", "Materiales eléctricos", 2)
            cat_plomeria = categorias.crear("Plomería", "Cañerías y accesorios", 3)
            print("Categorías creadas")
        else:
            cats = {c.nombre: c for c in categorias_repo.list()}
            cat_ferreteria = cats.get("Ferretería general") or categorias.crear("Ferretería general", None, 1)
            cat_electricidad = cats.get("Electricidad") or categorias.crear("Electricidad", None, 2)
            cat_plomeria = cats.get("Plomería") or categorias.crear("Plomería", None, 3)

        if not productos_repo.list():
            productos_creados = [
                productos.crear("Martillo carpintero 16oz", "Mango de fibra de vidrio", cat_ferreteria.id, 45000, None, 5, "pz"),
                productos.crear("Taladro percutor 1/2\"", "650W, incluye maletín", cat_ferreteria.id, 380000, None, 3, "pz"),
                productos.crear("Cable eléctrico 2.5mm (rollo 100m)", "THHN", cat_electricidad.id, 220000, None, 4, "rollo"),
                productos.crear("Llave térmica 20A", "Monopolar", cat_electricidad.id, 35000, None, 10, "pz"),
                productos.crear("Caño PVC 1/2\" (barra 6m)", "Para agua fría", cat_plomeria.id, 18000, None, 20, "pz"),
                productos.crear("Cinta teflón", "Rollo 10m", cat_plomeria.id, 3000, None, 30, "pz"),
                productos.crear("Tornillos autorroscantes 1\" (caja 100)", None, cat_ferreteria.id, 15000, None, 8, "caja"),
                productos.crear("Llave de paso 1/2\"", "Bronce", cat_plomeria.id, 28000, None, 6, "pz"),
            ]
            inventario = InventarioService(productos_repo, SqlAlchemyMovimientoInventarioRepository(db))
            for p in productos_creados:
                inventario.ajustar_stock(p.id, p.stock_minimo * 3, "Inventario inicial (demo)", demo_user.id)
            print(f"{len(productos_creados)} productos creados con stock inicial")
        else:
            productos_creados = productos_repo.list()

        if not clientes_repo.list():
            cliente_1 = clientes.crear(nombre="Construcciones Ybytu S.A.", ruc="80012345-6", telefono="0981234567", email="compras@ybytu.com.py", direccion="Av. Mcal. López 1234", ciudad="Asunción", notas=None)
            cliente_2 = clientes.crear(nombre="Ferretería El Tornillo Feliz", ruc="80098765-4", telefono="0982111222", email="pedidos@tornillofeliz.com.py", direccion="Ruta 2 km 15", ciudad="San Lorenzo", notas=None)
            print("Clientes creados")
        else:
            cliente_1, cliente_2 = clientes_repo.list()[:2] if len(clientes_repo.list()) >= 2 else (clientes_repo.list()[0], clientes_repo.list()[0])

        if not proveedores_repo.list():
            prov_1 = proveedores.crear(razon_social="Distribuidora Central Ferretera", ruc="80011111-1", email="ventas@central-ferretera.com.py", password="proveedor123", telefono="0985111111", direccion="Zona Industrial 1", ciudad="Luque", rubros="Ferretería, herramientas")
            prov_2 = proveedores.crear(razon_social="ElectroPar Mayorista", ruc="80022222-2", email="ventas@electropar.com.py", password="proveedor123", telefono="0985222222", direccion="Av. Aviadores del Chaco 500", ciudad="Asunción", rubros="Materiales eléctricos")
            print("Proveedores creados (usuario/clave: ver arriba, password 'proveedor123')")

            for p in productos_creados[:5]:
                catalogo.crear(prov_1.id, p.id, precio=int(p.precio_compra * 0.95), tiempo_entrega_dias=3)
            for p in productos_creados[2:4]:
                catalogo.crear(prov_2.id, p.id, precio=int(p.precio_compra * 0.9), tiempo_entrega_dias=2)
            print("Catálogo de proveedores cargado")
        else:
            prov_1, prov_2 = proveedores_repo.list()[:2]

        if not pedidos_repo.list():
            pedido_demo = pedidos.crear(
                usuario_id=demo_user.id,
                items=[
                    {"producto_id": productos_creados[0].id, "cantidad": 10, "precio_unitario": productos_creados[0].precio_venta},
                    {"producto_id": productos_creados[2].id, "cantidad": 5, "precio_unitario": productos_creados[2].precio_venta},
                ],
                cliente_id=cliente_1.id, fecha_pedido=hoy(), notas="Pedido de ejemplo para la demo",
            )
            print(f"Pedido demo creado: {pedido_demo.numero}")

        db.commit()

        # Catálogo y clientes más completos: con 8 productos la demo se ve vacía.
        cats = {c.nombre: c for c in categorias_repo.list()}
        for nombre, descripcion, orden in CATEGORIAS_EXTRA:
            if nombre not in cats:
                cats[nombre] = categorias.crear(nombre, descripcion, orden)
        existentes = {p.nombre for p in productos_repo.list()}
        nuevos = 0
        for nombre, categoria, compra, minimo, unidad in PRODUCTOS_EXTRA:
            if nombre not in existentes:
                productos.crear(nombre, None, cats[categoria].id, compra, None, minimo, unidad)
                nuevos += 1
        nombres_clientes = {c.nombre for c in clientes_repo.list()}
        for datos in CLIENTES_EXTRA:
            if datos["nombre"] not in nombres_clientes:
                clientes.crear(**datos, notas=None)
        db.commit()
        if nuevos:
            print(f"{nuevos} productos más en el catálogo de demo")

        # Varias semanas de ventas, con stock y caja coherentes.
        vendedor = usuarios.get_by_email(USUARIOS_DEMO[2][0])
        ventas = generar_historial(db, usuario_id=demo_user.id, vendedor_id=vendedor.id if vendedor else None)
        db.commit()
        if ventas:
            print(f"Historial de demo: {ventas} ventas de mostrador")
        a_cuenta = completar_medios_de_pago(db, usuario_id=demo_user.id)
        db.commit()
        if a_cuenta:
            print(f"Cuenta corriente de demo: {a_cuenta} ventas a cuenta")

        # Pedidos de clientes en distintas etapas (uno entregado y uno listo para enviar, desde stock).
        if len(pedidos_repo.list()) < 3:
            turnos_repo = SqlAlchemyCajaTurnoRepository(db)
            cobros = CobroPedidoService(
                pedidos_repo, SqlAlchemyPagoPedidoRepository(db), turnos_repo,
                CuentaCorrienteService(SqlAlchemyCuentaCorrienteRepository(db), clientes_repo, turnos_repo),
            )
            envios = OrdenEnvioService(
                SqlAlchemyOrdenEnvioRepository(db), productos_repo, SqlAlchemyMovimientoInventarioRepository(db), pedidos_repo,
                cobros, empresa_repo,
            )
            por_nombre = {p.nombre: p for p in productos_repo.list()}
            for cliente, lineas, entregar in [
                (cliente_2, [("Cemento portland 50kg", 10), ("Caño PVC 1/2\" (barra 6m)", 12)], True),
                (cliente_1, [("Pintura látex interior blanco 20L", 2), ("Rodillo antigota 23cm", 3)], False),
            ]:
                items = [
                    {"producto_id": por_nombre[n].id, "cantidad": c, "precio_unitario": por_nombre[n].precio_venta}
                    for n, c in lineas if n in por_nombre and por_nombre[n].stock_actual >= c
                ]
                if not items:
                    continue
                pedido = pedidos.crear(usuario_id=demo_user.id, items=items, cliente_id=cliente.id, fecha_pedido=hoy())
                orden = envios.crear(
                    usuario_id=demo_user.id, pedido_cliente_id=pedido.id, direccion_entrega=cliente.direccion or "A coordinar",
                    items=[{"producto_id": i["producto_id"], "cantidad": i["cantidad"]} for i in items],
                    contacto_entrega=cliente.nombre, telefono_entrega=cliente.telefono, metodo_envio="Camión propio",
                )
                if entregar:
                    envios.marcar_lista_despacho(orden.id)
                    envios.despachar(orden.id, None, demo_user.id)
                    envios.entregar(orden.id, "Recibido conforme")
            db.commit()
            print("Pedidos de demo en distintas etapas")

        # Unidades averiadas, vencidas, etc. y un reclamo enviado a un proveedor.
        deposito = usuarios.get_by_email(USUARIOS_DEMO[3][0])
        no_vendibles = cargar_stock_no_vendible(db, usuario_id=deposito.id if deposito else demo_user.id)
        db.commit()
        if no_vendibles:
            print(f"Stock no vendible de demo: {no_vendibles} registros y un reclamo al proveedor")

        # Pedidos con logística y cobro: pagado a retirar, pagado a entregar,
        # con seña, entregado a cuenta y contra entrega por rendir.
        vendedor = usuarios.get_by_email(USUARIOS_DEMO[2][0])
        con_logistica = cargar_logistica(
            db, vendedor_id=vendedor.id if vendedor else demo_user.id, deposito_id=deposito.id if deposito else demo_user.id,
        )
        db.commit()
        if con_logistica:
            print(f"Logística de demo: {con_logistica} pedidos con distintas formas de entrega y cobro")

        print("\nListo. Datos demo sembrados correctamente.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
