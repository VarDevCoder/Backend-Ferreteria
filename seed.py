"""Siembra datos de ejemplo para la demo: el usuario interno fijo que usan los
endpoints (no hay login), categorías, productos, clientes, proveedores con su
catálogo, y un par de pedidos ya avanzados en distintos puntos del flujo para
que la demo no arranque con las pantallas vacías.

Uso:
    python seed.py            # crea los datos si no existen (idempotente)
    python seed.py --reset    # borra todo el esquema y lo vuelve a crear
"""
from __future__ import annotations

import sys
from datetime import date

from app.application.services.catalogo_service import CategoriaService, ProductoService
from app.application.services.contactos_service import ClienteService, ProveedorProductoService, ProveedorService
from app.application.services.orden_compra_service import OrdenCompraService
from app.application.services.pedido_cliente_service import PedidoClienteService
from app.application.services.solicitud_presupuesto_service import SolicitudPresupuestoService
from app.domain.entities import Usuario
from app.domain.enums import RolUsuario
from app.infrastructure.db.models import Base
from app.infrastructure.db.repositories.catalogo_repository import SqlAlchemyCategoriaRepository, SqlAlchemyProductoRepository
from app.infrastructure.db.repositories.contactos_repository import (
    SqlAlchemyClienteRepository,
    SqlAlchemyProveedorProductoRepository,
    SqlAlchemyProveedorRepository,
)
from app.infrastructure.db.repositories.flujo_repository import (
    SqlAlchemyMovimientoInventarioRepository,
    SqlAlchemyOrdenCompraRepository,
    SqlAlchemyPedidoClienteRepository,
    SqlAlchemySolicitudPresupuestoRepository,
)
from app.infrastructure.db.repositories.usuario_repository import SqlAlchemyUsuarioRepository
from app.infrastructure.db.session import SessionLocal, engine
from app.infrastructure.security.password_hasher import hash_password
from app.interfaces.api.deps import DEMO_USER_EMAIL


def main() -> None:
    if "--reset" in sys.argv:
        print("Recreando el esquema completo...")
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

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
        pedidos = PedidoClienteService(pedidos_repo, clientes_repo, proveedores_repo, solicitudes_repo)
        solicitudes = SolicitudPresupuestoService(solicitudes_repo, proveedores_repo, pedidos_repo, ordenes_compra_repo)
        OrdenCompraService(ordenes_compra_repo, productos_repo, SqlAlchemyMovimientoInventarioRepository(db), pedidos_repo)

        demo_user = usuarios.get_by_email(DEMO_USER_EMAIL)
        if demo_user is None:
            demo_user = usuarios.add(
                Usuario(
                    id=None, name="Usuario Demo", email=DEMO_USER_EMAIL,
                    password_hash=hash_password("demo12345"), rol=RolUsuario.ADMIN,
                )
            )
            print(f"Usuario demo creado (id={demo_user.id})")

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
            print(f"{len(productos_creados)} productos creados")
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
                cliente_id=cliente_1.id, fecha_pedido=date.today(), notas="Pedido de ejemplo para la demo",
            )
            print(f"Pedido demo creado: {pedido_demo.numero}")

        db.commit()
        print("\nListo. Datos demo sembrados correctamente.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
