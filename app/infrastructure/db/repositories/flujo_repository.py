"""Repositorios del ciclo comercial: PedidoCliente, SolicitudPresupuesto,
OrdenCompra, OrdenEnvio y MovimientoInventario.

Van en un solo módulo porque comparten el mismo patrón (documento + items) y
porque casi siempre se consultan/actualizan en conjunto dentro de los mismos
casos de uso — separarlos en cinco archivos no aportaría claridad extra.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.entities import (
    MovimientoInventario,
    OrdenCompra,
    OrdenCompraItem,
    OrdenEnvio,
    OrdenEnvioItem,
    PedidoCliente,
    PedidoClienteItem,
    SolicitudPresupuesto,
    SolicitudPresupuestoItem,
)
from app.domain.enums import (
    EstadoOrdenCompra,
    EstadoOrdenEnvio,
    EstadoPedidoCliente,
    EstadoSolicitudPresupuesto,
    TipoMovimientoInventario,
    TipoReferenciaMovimiento,
)
from app.infrastructure.db.models import (
    MovimientoInventarioModel,
    OrdenCompraItemModel,
    OrdenCompraModel,
    OrdenEnvioItemModel,
    OrdenEnvioModel,
    PedidoClienteItemModel,
    PedidoClienteModel,
    SolicitudPresupuestoItemModel,
    SolicitudPresupuestoModel,
)


class SqlAlchemyPedidoClienteRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, estado: str | None = None, busqueda: str | None = None) -> list[PedidoCliente]:
        stmt = (
            select(PedidoClienteModel)
            .options(selectinload(PedidoClienteModel.items))
            .order_by(PedidoClienteModel.created_at.desc())
        )
        if estado:
            stmt = stmt.where(PedidoClienteModel.estado == estado)
        if busqueda:
            patron = f"%{busqueda}%"
            stmt = stmt.where(
                PedidoClienteModel.numero.ilike(patron)
                | PedidoClienteModel.cliente_nombre.ilike(patron)
                | PedidoClienteModel.cliente_ruc.ilike(patron)
            )
        rows = self._session.execute(stmt).unique().scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, pedido_id: int) -> PedidoCliente | None:
        row = self._session.get(
            PedidoClienteModel, pedido_id, options=[selectinload(PedidoClienteModel.items)]
        )
        return self._to_entity(row) if row else None

    def add(self, pedido: PedidoCliente) -> PedidoCliente:
        row = PedidoClienteModel(
            numero=pedido.numero,
            usuario_id=pedido.usuario_id,
            cliente_id=pedido.cliente_id,
            cliente_nombre=pedido.cliente_nombre,
            cliente_ruc=pedido.cliente_ruc,
            cliente_telefono=pedido.cliente_telefono,
            cliente_email=pedido.cliente_email,
            cliente_direccion=pedido.cliente_direccion,
            fecha_pedido=pedido.fecha_pedido,
            fecha_entrega_solicitada=pedido.fecha_entrega_solicitada,
            fecha_entrega_estimada=pedido.fecha_entrega_estimada,
            estado=pedido.estado.value,
            subtotal=pedido.subtotal,
            descuento=pedido.descuento,
            total=pedido.total,
            notas=pedido.notas,
            items=[
                PedidoClienteItemModel(
                    producto_id=i.producto_id, cantidad=i.cantidad, precio_unitario=i.precio_unitario,
                    subtotal=i.subtotal,
                )
                for i in pedido.items
            ],
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, pedido: PedidoCliente) -> PedidoCliente:
        row = self._session.get(PedidoClienteModel, pedido.id)
        if row is None:
            raise ValueError(f"PedidoCliente {pedido.id} no existe")
        row.cliente_id = pedido.cliente_id
        row.cliente_nombre = pedido.cliente_nombre
        row.cliente_ruc = pedido.cliente_ruc
        row.cliente_telefono = pedido.cliente_telefono
        row.cliente_email = pedido.cliente_email
        row.cliente_direccion = pedido.cliente_direccion
        row.fecha_entrega_solicitada = pedido.fecha_entrega_solicitada
        row.fecha_entrega_estimada = pedido.fecha_entrega_estimada
        row.estado = pedido.estado.value
        row.subtotal = pedido.subtotal
        row.descuento = pedido.descuento
        row.total = pedido.total
        row.notas = pedido.notas
        row.motivo_cancelacion = pedido.motivo_cancelacion
        self._session.flush()
        return self._to_entity(row)

    def replace_items(self, pedido_id: int, items: list[PedidoClienteItem]) -> None:
        row = self._session.get(PedidoClienteModel, pedido_id, options=[selectinload(PedidoClienteModel.items)])
        if row is None:
            raise ValueError(f"PedidoCliente {pedido_id} no existe")
        row.items.clear()
        self._session.flush()
        for item in items:
            row.items.append(
                PedidoClienteItemModel(
                    producto_id=item.producto_id, cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario, subtotal=item.subtotal,
                )
            )
        self._session.flush()

    def delete(self, pedido_id: int) -> None:
        row = self._session.get(PedidoClienteModel, pedido_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    def siguiente_numero(self) -> str:
        ultimo_id = self._session.execute(select(func.max(PedidoClienteModel.id))).scalar() or 0
        return f"Solicitud #{ultimo_id + 1}"

    def contar_activos(self) -> int:
        stmt = select(func.count()).select_from(PedidoClienteModel).where(
            PedidoClienteModel.estado.not_in([EstadoPedidoCliente.ENTREGADO, EstadoPedidoCliente.CANCELADO])
        )
        return self._session.execute(stmt).scalar_one()

    def contar_creados_hoy(self) -> int:
        stmt = select(func.count()).select_from(PedidoClienteModel).where(
            func.date(PedidoClienteModel.created_at) == func.current_date()
        )
        return self._session.execute(stmt).scalar_one()

    @staticmethod
    def _to_entity(row: PedidoClienteModel) -> PedidoCliente:
        return PedidoCliente(
            id=row.id,
            numero=row.numero,
            usuario_id=row.usuario_id,
            cliente_id=row.cliente_id,
            cliente_nombre=row.cliente_nombre,
            cliente_ruc=row.cliente_ruc,
            cliente_telefono=row.cliente_telefono,
            cliente_email=row.cliente_email,
            cliente_direccion=row.cliente_direccion,
            fecha_pedido=row.fecha_pedido,
            fecha_entrega_solicitada=row.fecha_entrega_solicitada,
            fecha_entrega_estimada=row.fecha_entrega_estimada,
            estado=EstadoPedidoCliente(row.estado),
            subtotal=row.subtotal,
            descuento=row.descuento,
            total=row.total,
            notas=row.notas,
            motivo_cancelacion=row.motivo_cancelacion,
            created_at=row.created_at,
            items=[
                PedidoClienteItem(
                    id=i.id, pedido_cliente_id=i.pedido_cliente_id, producto_id=i.producto_id,
                    cantidad=i.cantidad, precio_unitario=i.precio_unitario, subtotal=i.subtotal,
                )
                for i in row.items
            ],
        )


class SqlAlchemySolicitudPresupuestoRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(
        self, estado: str | None = None, proveedor_id: int | None = None, pedido_cliente_id: int | None = None
    ) -> list[SolicitudPresupuesto]:
        stmt = (
            select(SolicitudPresupuestoModel)
            .options(selectinload(SolicitudPresupuestoModel.items))
            .order_by(SolicitudPresupuestoModel.created_at.desc())
        )
        if estado:
            stmt = stmt.where(SolicitudPresupuestoModel.estado == estado)
        if proveedor_id is not None:
            stmt = stmt.where(SolicitudPresupuestoModel.proveedor_id == proveedor_id)
        if pedido_cliente_id is not None:
            stmt = stmt.where(SolicitudPresupuestoModel.pedido_cliente_id == pedido_cliente_id)
        rows = self._session.execute(stmt).unique().scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, solicitud_id: int) -> SolicitudPresupuesto | None:
        row = self._session.get(
            SolicitudPresupuestoModel, solicitud_id, options=[selectinload(SolicitudPresupuestoModel.items)]
        )
        return self._to_entity(row) if row else None

    def add(self, solicitud: SolicitudPresupuesto) -> SolicitudPresupuesto:
        row = SolicitudPresupuestoModel(
            numero=solicitud.numero,
            pedido_cliente_id=solicitud.pedido_cliente_id,
            proveedor_id=solicitud.proveedor_id,
            usuario_id=solicitud.usuario_id,
            fecha_solicitud=solicitud.fecha_solicitud,
            fecha_limite_respuesta=solicitud.fecha_limite_respuesta,
            estado=solicitud.estado.value,
            mensaje_solicitud=solicitud.mensaje_solicitud,
            items=[
                SolicitudPresupuestoItemModel(
                    producto_id=i.producto_id, cantidad_solicitada=i.cantidad_solicitada
                )
                for i in solicitud.items
            ],
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, solicitud: SolicitudPresupuesto) -> SolicitudPresupuesto:
        row = self._session.get(
            SolicitudPresupuestoModel, solicitud.id, options=[selectinload(SolicitudPresupuestoModel.items)]
        )
        if row is None:
            raise ValueError(f"SolicitudPresupuesto {solicitud.id} no existe")
        row.estado = solicitud.estado.value
        row.respuesta_proveedor = solicitud.respuesta_proveedor
        row.dias_entrega_estimados = solicitud.dias_entrega_estimados
        row.total_cotizado = solicitud.total_cotizado
        row.fecha_respuesta = solicitud.fecha_respuesta

        items_por_id = {i.id: i for i in row.items}
        for item in solicitud.items:
            fila = items_por_id.get(item.id)
            if fila is None:
                continue
            fila.tiene_stock = item.tiene_stock
            fila.cantidad_disponible = item.cantidad_disponible
            fila.precio_unitario_cotizado = item.precio_unitario_cotizado
            fila.subtotal_cotizado = item.subtotal_cotizado
        self._session.flush()
        return self._to_entity(row)

    def delete(self, solicitud_id: int) -> None:
        row = self._session.get(SolicitudPresupuestoModel, solicitud_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    def siguiente_numero(self) -> str:
        anio = self._session.execute(select(func.extract("year", func.current_date()))).scalar_one()
        anio = int(anio)
        stmt = select(func.count()).select_from(SolicitudPresupuestoModel).where(
            func.extract("year", SolicitudPresupuestoModel.created_at) == anio
        )
        cantidad = self._session.execute(stmt).scalar_one()
        return f"SP-{anio}-{cantidad + 1:04d}"

    def existe_activa(self, pedido_cliente_id: int, proveedor_id: int) -> bool:
        stmt = select(SolicitudPresupuestoModel.id).where(
            SolicitudPresupuestoModel.pedido_cliente_id == pedido_cliente_id,
            SolicitudPresupuestoModel.proveedor_id == proveedor_id,
            SolicitudPresupuestoModel.estado.not_in(
                [EstadoSolicitudPresupuesto.RECHAZADA, EstadoSolicitudPresupuesto.VENCIDA]
            ),
        )
        return self._session.execute(stmt).first() is not None

    def contar_pendientes(self) -> int:
        stmt = select(func.count()).select_from(SolicitudPresupuestoModel).where(
            SolicitudPresupuestoModel.estado.in_(
                [EstadoSolicitudPresupuesto.ENVIADA, EstadoSolicitudPresupuesto.VISTA]
            )
        )
        return self._session.execute(stmt).scalar_one()

    def contar_cotizadas(self) -> int:
        stmt = select(func.count()).select_from(SolicitudPresupuestoModel).where(
            SolicitudPresupuestoModel.estado == EstadoSolicitudPresupuesto.COTIZADA
        )
        return self._session.execute(stmt).scalar_one()

    @staticmethod
    def _to_entity(row: SolicitudPresupuestoModel) -> SolicitudPresupuesto:
        return SolicitudPresupuesto(
            id=row.id,
            numero=row.numero,
            proveedor_id=row.proveedor_id,
            usuario_id=row.usuario_id,
            pedido_cliente_id=row.pedido_cliente_id,
            fecha_solicitud=row.fecha_solicitud,
            fecha_limite_respuesta=row.fecha_limite_respuesta,
            fecha_respuesta=row.fecha_respuesta,
            estado=EstadoSolicitudPresupuesto(row.estado),
            mensaje_solicitud=row.mensaje_solicitud,
            respuesta_proveedor=row.respuesta_proveedor,
            total_cotizado=row.total_cotizado,
            dias_entrega_estimados=row.dias_entrega_estimados,
            created_at=row.created_at,
            items=[
                SolicitudPresupuestoItem(
                    id=i.id, solicitud_presupuesto_id=i.solicitud_presupuesto_id, producto_id=i.producto_id,
                    cantidad_solicitada=i.cantidad_solicitada, tiene_stock=i.tiene_stock,
                    cantidad_disponible=i.cantidad_disponible,
                    precio_unitario_cotizado=i.precio_unitario_cotizado, subtotal_cotizado=i.subtotal_cotizado,
                )
                for i in row.items
            ],
        )


class SqlAlchemyOrdenCompraRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, estado: str | None = None, busqueda: str | None = None) -> list[OrdenCompra]:
        stmt = (
            select(OrdenCompraModel)
            .options(selectinload(OrdenCompraModel.items))
            .order_by(OrdenCompraModel.created_at.desc())
        )
        if estado:
            stmt = stmt.where(OrdenCompraModel.estado == estado)
        if busqueda:
            patron = f"%{busqueda}%"
            stmt = stmt.where(
                OrdenCompraModel.numero.ilike(patron) | OrdenCompraModel.proveedor_nombre.ilike(patron)
            )
        rows = self._session.execute(stmt).unique().scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, orden_id: int) -> OrdenCompra | None:
        row = self._session.get(OrdenCompraModel, orden_id, options=[selectinload(OrdenCompraModel.items)])
        return self._to_entity(row) if row else None

    def add(self, orden: OrdenCompra) -> OrdenCompra:
        row = OrdenCompraModel(
            numero=orden.numero,
            usuario_id=orden.usuario_id,
            pedido_cliente_id=orden.pedido_cliente_id,
            proveedor_nombre=orden.proveedor_nombre,
            proveedor_ruc=orden.proveedor_ruc,
            proveedor_telefono=orden.proveedor_telefono,
            proveedor_email=orden.proveedor_email,
            proveedor_direccion=orden.proveedor_direccion,
            fecha_orden=orden.fecha_orden,
            fecha_entrega_esperada=orden.fecha_entrega_esperada,
            estado=orden.estado.value,
            subtotal=orden.subtotal,
            descuento=orden.descuento,
            total=orden.total,
            notas=orden.notas,
            items=[
                OrdenCompraItemModel(
                    producto_id=i.producto_id, cantidad_solicitada=i.cantidad_solicitada,
                    precio_unitario=i.precio_unitario, subtotal=i.subtotal,
                )
                for i in orden.items
            ],
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, orden: OrdenCompra) -> OrdenCompra:
        row = self._session.get(OrdenCompraModel, orden.id, options=[selectinload(OrdenCompraModel.items)])
        if row is None:
            raise ValueError(f"OrdenCompra {orden.id} no existe")
        row.proveedor_nombre = orden.proveedor_nombre
        row.proveedor_ruc = orden.proveedor_ruc
        row.proveedor_telefono = orden.proveedor_telefono
        row.proveedor_email = orden.proveedor_email
        row.proveedor_direccion = orden.proveedor_direccion
        row.fecha_entrega_esperada = orden.fecha_entrega_esperada
        row.fecha_recepcion = orden.fecha_recepcion
        row.estado = orden.estado.value
        row.subtotal = orden.subtotal
        row.descuento = orden.descuento
        row.total = orden.total
        row.notas = orden.notas
        row.motivo_cancelacion = orden.motivo_cancelacion

        items_por_id = {i.id: i for i in row.items}
        for item in orden.items:
            fila = items_por_id.get(item.id)
            if fila is not None:
                fila.cantidad_recibida = item.cantidad_recibida
        self._session.flush()
        return self._to_entity(row)

    def replace_items(self, orden_id: int, items: list[OrdenCompraItem]) -> None:
        row = self._session.get(OrdenCompraModel, orden_id, options=[selectinload(OrdenCompraModel.items)])
        if row is None:
            raise ValueError(f"OrdenCompra {orden_id} no existe")
        row.items.clear()
        self._session.flush()
        for item in items:
            row.items.append(
                OrdenCompraItemModel(
                    producto_id=item.producto_id, cantidad_solicitada=item.cantidad_solicitada,
                    precio_unitario=item.precio_unitario, subtotal=item.subtotal,
                )
            )
        self._session.flush()

    def delete(self, orden_id: int) -> None:
        row = self._session.get(OrdenCompraModel, orden_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    def siguiente_numero(self) -> str:
        anio = int(self._session.execute(select(func.extract("year", func.current_date()))).scalar_one())
        stmt = select(func.count()).select_from(OrdenCompraModel).where(
            func.extract("year", OrdenCompraModel.created_at) == anio
        )
        cantidad = self._session.execute(stmt).scalar_one()
        return f"OC-{anio}-{cantidad + 1:04d}"

    def contar_activas(self) -> int:
        stmt = select(func.count()).select_from(OrdenCompraModel).where(
            OrdenCompraModel.estado.not_in([EstadoOrdenCompra.RECIBIDA_COMPLETA, EstadoOrdenCompra.CANCELADA])
        )
        return self._session.execute(stmt).scalar_one()

    @staticmethod
    def _to_entity(row: OrdenCompraModel) -> OrdenCompra:
        return OrdenCompra(
            id=row.id,
            numero=row.numero,
            usuario_id=row.usuario_id,
            pedido_cliente_id=row.pedido_cliente_id,
            proveedor_nombre=row.proveedor_nombre,
            proveedor_ruc=row.proveedor_ruc,
            proveedor_telefono=row.proveedor_telefono,
            proveedor_email=row.proveedor_email,
            proveedor_direccion=row.proveedor_direccion,
            fecha_orden=row.fecha_orden,
            fecha_entrega_esperada=row.fecha_entrega_esperada,
            fecha_recepcion=row.fecha_recepcion,
            estado=EstadoOrdenCompra(row.estado),
            subtotal=row.subtotal,
            descuento=row.descuento,
            total=row.total,
            notas=row.notas,
            motivo_cancelacion=row.motivo_cancelacion,
            created_at=row.created_at,
            items=[
                OrdenCompraItem(
                    id=i.id, orden_compra_id=i.orden_compra_id, producto_id=i.producto_id,
                    cantidad_solicitada=i.cantidad_solicitada, precio_unitario=i.precio_unitario,
                    cantidad_recibida=i.cantidad_recibida, subtotal=i.subtotal,
                )
                for i in row.items
            ],
        )


class SqlAlchemyOrdenEnvioRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, estado: str | None = None, busqueda: str | None = None) -> list[OrdenEnvio]:
        stmt = (
            select(OrdenEnvioModel)
            .options(selectinload(OrdenEnvioModel.items))
            .order_by(OrdenEnvioModel.created_at.desc())
        )
        if estado:
            stmt = stmt.where(OrdenEnvioModel.estado == estado)
        if busqueda:
            patron = f"%{busqueda}%"
            stmt = stmt.where(
                OrdenEnvioModel.numero.ilike(patron) | OrdenEnvioModel.numero_guia.ilike(patron)
            )
        rows = self._session.execute(stmt).unique().scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, orden_id: int) -> OrdenEnvio | None:
        row = self._session.get(OrdenEnvioModel, orden_id, options=[selectinload(OrdenEnvioModel.items)])
        return self._to_entity(row) if row else None

    def add(self, orden: OrdenEnvio) -> OrdenEnvio:
        row = OrdenEnvioModel(
            numero=orden.numero,
            usuario_id=orden.usuario_id,
            pedido_cliente_id=orden.pedido_cliente_id,
            direccion_entrega=orden.direccion_entrega,
            contacto_entrega=orden.contacto_entrega,
            telefono_entrega=orden.telefono_entrega,
            fecha_generacion=orden.fecha_generacion,
            metodo_envio=orden.metodo_envio,
            transportista=orden.transportista,
            notas=orden.notas,
            estado=orden.estado.value,
            items=[OrdenEnvioItemModel(producto_id=i.producto_id, cantidad=i.cantidad) for i in orden.items],
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, orden: OrdenEnvio) -> OrdenEnvio:
        row = self._session.get(OrdenEnvioModel, orden.id)
        if row is None:
            raise ValueError(f"OrdenEnvio {orden.id} no existe")
        row.estado = orden.estado.value
        row.fecha_envio = orden.fecha_envio
        row.fecha_entrega = orden.fecha_entrega
        row.numero_guia = orden.numero_guia
        row.observaciones_entrega = orden.observaciones_entrega
        self._session.flush()
        return self._to_entity(row)

    def delete(self, orden_id: int) -> None:
        row = self._session.get(OrdenEnvioModel, orden_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    def siguiente_numero(self) -> str:
        anio = int(self._session.execute(select(func.extract("year", func.current_date()))).scalar_one())
        stmt = select(func.count()).select_from(OrdenEnvioModel).where(
            func.extract("year", OrdenEnvioModel.created_at) == anio
        )
        cantidad = self._session.execute(stmt).scalar_one()
        return f"ENV-{anio}-{cantidad + 1:04d}"

    def contar_pendientes(self) -> int:
        stmt = select(func.count()).select_from(OrdenEnvioModel).where(
            OrdenEnvioModel.estado.not_in(
                [EstadoOrdenEnvio.ENTREGADO, EstadoOrdenEnvio.CANCELADO, EstadoOrdenEnvio.DEVUELTO]
            )
        )
        return self._session.execute(stmt).scalar_one()

    @staticmethod
    def _to_entity(row: OrdenEnvioModel) -> OrdenEnvio:
        return OrdenEnvio(
            id=row.id,
            numero=row.numero,
            usuario_id=row.usuario_id,
            pedido_cliente_id=row.pedido_cliente_id,
            direccion_entrega=row.direccion_entrega,
            contacto_entrega=row.contacto_entrega,
            telefono_entrega=row.telefono_entrega,
            fecha_generacion=row.fecha_generacion,
            fecha_envio=row.fecha_envio,
            fecha_entrega=row.fecha_entrega,
            estado=EstadoOrdenEnvio(row.estado),
            metodo_envio=row.metodo_envio,
            numero_guia=row.numero_guia,
            transportista=row.transportista,
            notas=row.notas,
            observaciones_entrega=row.observaciones_entrega,
            created_at=row.created_at,
            items=[
                OrdenEnvioItem(id=i.id, orden_envio_id=i.orden_envio_id, producto_id=i.producto_id, cantidad=i.cantidad)
                for i in row.items
            ],
        )


class SqlAlchemyMovimientoInventarioRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, movimiento: MovimientoInventario) -> MovimientoInventario:
        row = MovimientoInventarioModel(
            producto_id=movimiento.producto_id,
            tipo=movimiento.tipo.value,
            cantidad=movimiento.cantidad,
            stock_anterior=movimiento.stock_anterior,
            stock_nuevo=movimiento.stock_nuevo,
            referencia_tipo=movimiento.referencia_tipo.value,
            referencia_id=movimiento.referencia_id,
            usuario_id=movimiento.usuario_id,
            observaciones=movimiento.observaciones,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def list(
        self, producto_id: int | None = None, tipo: str | None = None, limit: int | None = None
    ) -> list[MovimientoInventario]:
        stmt = select(MovimientoInventarioModel).order_by(MovimientoInventarioModel.created_at.desc())
        if producto_id is not None:
            stmt = stmt.where(MovimientoInventarioModel.producto_id == producto_id)
        if tipo:
            stmt = stmt.where(MovimientoInventarioModel.tipo == tipo)
        if limit:
            stmt = stmt.limit(limit)
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_entity(r) for r in rows]

    @staticmethod
    def _to_entity(row: MovimientoInventarioModel) -> MovimientoInventario:
        return MovimientoInventario(
            id=row.id,
            producto_id=row.producto_id,
            tipo=TipoMovimientoInventario(row.tipo),
            cantidad=row.cantidad,
            stock_anterior=row.stock_anterior,
            stock_nuevo=row.stock_nuevo,
            referencia_tipo=TipoReferenciaMovimiento(row.referencia_tipo),
            referencia_id=row.referencia_id,
            usuario_id=row.usuario_id,
            observaciones=row.observaciones,
            created_at=row.created_at,
        )
