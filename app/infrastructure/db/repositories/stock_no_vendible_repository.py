"""Repositorios de stock no vendible y reclamos al proveedor.

Los nombres de producto, proveedor y usuario se resuelven con joins al leer
(una consulta por listado) para que las pantallas y el documento del reclamo
no tengan que pedir cada dato por separado.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, cast, func, select, text
from sqlalchemy.orm import Session, aliased, selectinload

from app.domain.entities import (
    Producto,
    ReclamoProveedor,
    ReclamoProveedorItem,
    ResolucionNoVendible,
    StockNoVendible,
)
from app.domain.enums import (
    EstadoReclamoProveedor,
    EstadoStockNoVendible,
    MotivoNoVendible,
    ResolucionItemReclamo,
    TipoResolucionNoVendible,
)
from app.infrastructure.db.models import (
    OrdenCompraModel,
    ProductoModel,
    ProveedorModel,
    ReclamoProveedorItemModel,
    ReclamoProveedorModel,
    ResolucionNoVendibleModel,
    StockNoVendibleModel,
    UsuarioModel,
)

# Lock transaccional para numerar reclamos sin duplicados entre requests simultáneos.
_LOCK_NUMERO_RECLAMO = 7_301_956
_ESTADOS_ABIERTOS = [e.value for e in ReclamoProveedor.ESTADOS_ABIERTOS]


def _dec(valor) -> Decimal:
    return Decimal(str(valor if valor is not None else 0))


class SqlAlchemyStockNoVendibleRepository:
    def __init__(self, session: Session):
        self._session = session

    def ahora(self) -> datetime:
        """Reloj de la base: el mismo que usan los `created_at`."""
        return self._session.execute(select(func.now())).scalar_one().replace(tzinfo=None)

    # --- Stock del producto ---------------------------------------------------

    def bloquear_producto(self, producto_id: int) -> Producto | None:
        row = self._session.get(ProductoModel, producto_id, with_for_update=True, populate_existing=True)
        if row is None:
            return None
        return Producto(
            id=row.id, codigo=row.codigo, nombre=row.nombre, descripcion=row.descripcion,
            categoria_id=row.categoria_id, precio_compra=row.precio_compra, precio_venta=row.precio_venta,
            stock_actual=_dec(row.stock_actual), stock_minimo=_dec(row.stock_minimo),
            unidad_medida=row.unidad_medida, activo=row.activo, stock_no_vendible=_dec(row.stock_no_vendible),
        )

    def guardar_stock(self, producto_id: int, stock_vendible: Decimal, stock_no_vendible: Decimal) -> None:
        row = self._session.get(ProductoModel, producto_id)
        row.stock_actual = stock_vendible
        row.stock_no_vendible = stock_no_vendible
        self._session.flush()

    def existe_orden_compra(self, orden_compra_id: int) -> bool:
        return self._session.execute(
            select(OrdenCompraModel.id).where(OrdenCompraModel.id == orden_compra_id)
        ).first() is not None

    # --- Registros ---------------------------------------------------------------

    def add(self, registro: StockNoVendible) -> StockNoVendible:
        row = StockNoVendibleModel(
            producto_id=registro.producto_id, cantidad=registro.cantidad, cantidad_pendiente=registro.cantidad_pendiente,
            motivo=registro.motivo.value, nota=registro.nota, proveedor_id=registro.proveedor_id,
            orden_compra_id=registro.orden_compra_id, costo_unitario=registro.costo_unitario,
            estado=registro.estado.value, usuario_id=registro.usuario_id,
        )
        self._session.add(row)
        self._session.flush()
        return self.get_by_id(row.id)

    def get_by_id(self, registro_id: int, bloquear: bool = False) -> StockNoVendible | None:
        registros = self.get_many([registro_id], bloquear=bloquear)
        return registros[0] if registros else None

    def get_many(self, registro_ids: list[int], bloquear: bool = False) -> list[StockNoVendible]:
        if not registro_ids:
            return []
        if bloquear:
            # Bloquea las filas en orden de id (evita interbloqueos) antes de leerlas.
            self._session.execute(
                select(StockNoVendibleModel.id).where(StockNoVendibleModel.id.in_(registro_ids))
                .order_by(StockNoVendibleModel.id).with_for_update()
            ).all()
        return self._consultar(StockNoVendibleModel.id.in_(registro_ids), con_resoluciones=True)

    def list(
        self, estado: str | None = None, producto_id: int | None = None,
        proveedor_id: int | None = None, motivo: str | None = None,
    ) -> list[StockNoVendible]:
        condiciones = []
        if estado:
            condiciones.append(StockNoVendibleModel.estado == estado)
        if producto_id is not None:
            condiciones.append(StockNoVendibleModel.producto_id == producto_id)
        if proveedor_id is not None:
            condiciones.append(StockNoVendibleModel.proveedor_id == proveedor_id)
        if motivo:
            condiciones.append(StockNoVendibleModel.motivo == motivo)
        return self._consultar(*condiciones, con_resoluciones=False)

    def update(self, registro: StockNoVendible) -> StockNoVendible:
        row = self._session.get(StockNoVendibleModel, registro.id)
        row.cantidad_pendiente = registro.cantidad_pendiente
        row.estado = registro.estado.value
        row.proveedor_id = registro.proveedor_id
        row.nota = registro.nota
        self._session.flush()
        return registro

    def agregar_resolucion(self, resolucion: ResolucionNoVendible) -> ResolucionNoVendible:
        row = ResolucionNoVendibleModel(
            registro_id=resolucion.registro_id, tipo=resolucion.tipo.value, cantidad=resolucion.cantidad,
            monto=resolucion.monto, reclamo_id=resolucion.reclamo_id, nota=resolucion.nota,
            usuario_id=resolucion.usuario_id,
        )
        self._session.add(row)
        self._session.flush()
        resolucion.id = row.id
        return resolucion

    def cantidades_en_reclamo(self, registro_ids: list[int], excluir_reclamo_id: int | None = None) -> dict[int, Decimal]:
        """Unidades de cada registro reservadas en reclamos abiertos y todavía sin resolución."""
        if not registro_ids:
            return {}
        stmt = (
            select(ReclamoProveedorItemModel.registro_id, func.sum(ReclamoProveedorItemModel.cantidad))
            .join(ReclamoProveedorModel, ReclamoProveedorModel.id == ReclamoProveedorItemModel.reclamo_id)
            .where(
                ReclamoProveedorItemModel.registro_id.in_(registro_ids),
                ReclamoProveedorItemModel.resolucion.is_(None),
                ReclamoProveedorModel.estado.in_(_ESTADOS_ABIERTOS),
            )
            .group_by(ReclamoProveedorItemModel.registro_id)
        )
        if excluir_reclamo_id is not None:
            stmt = stmt.where(ReclamoProveedorModel.id != excluir_reclamo_id)
        return {registro_id: _dec(total) for registro_id, total in self._session.execute(stmt).all()}

    def _consultar(self, *condiciones, con_resoluciones: bool) -> list[StockNoVendible]:
        stmt = (
            select(StockNoVendibleModel, ProductoModel.codigo, ProductoModel.nombre, ProductoModel.unidad_medida,
                   ProveedorModel.razon_social, UsuarioModel.name)
            .join(ProductoModel, ProductoModel.id == StockNoVendibleModel.producto_id)
            .outerjoin(ProveedorModel, ProveedorModel.id == StockNoVendibleModel.proveedor_id)
            .outerjoin(UsuarioModel, UsuarioModel.id == StockNoVendibleModel.usuario_id)
            .where(*condiciones)
            .order_by(StockNoVendibleModel.created_at.desc(), StockNoVendibleModel.id.desc())
        )
        if con_resoluciones:
            stmt = stmt.options(selectinload(StockNoVendibleModel.resoluciones))
        filas = self._session.execute(stmt).all()
        en_reclamo = self.cantidades_en_reclamo([f[0].id for f in filas])
        nombres_usuarios: dict[int, str] = {}
        if con_resoluciones:
            ids = {r.usuario_id for f in filas for r in f[0].resoluciones if r.usuario_id}
            if ids:
                nombres_usuarios = dict(self._session.execute(
                    select(UsuarioModel.id, UsuarioModel.name).where(UsuarioModel.id.in_(ids))
                ).all())
        registros = []
        for row, codigo, nombre, unidad, proveedor, usuario in filas:
            registro = StockNoVendible(
                id=row.id, producto_id=row.producto_id, cantidad=_dec(row.cantidad),
                cantidad_pendiente=_dec(row.cantidad_pendiente), motivo=MotivoNoVendible(row.motivo), nota=row.nota,
                proveedor_id=row.proveedor_id, orden_compra_id=row.orden_compra_id, costo_unitario=row.costo_unitario,
                estado=EstadoStockNoVendible(row.estado), usuario_id=row.usuario_id, created_at=row.created_at,
                updated_at=row.updated_at, cantidad_en_reclamo=en_reclamo.get(row.id, Decimal("0")),
                producto_codigo=codigo, producto_nombre=nombre, unidad_medida=unidad,
                proveedor_nombre=proveedor, usuario_nombre=usuario,
            )
            if con_resoluciones:
                registro.resoluciones = [
                    ResolucionNoVendible(
                        id=r.id, registro_id=r.registro_id, tipo=TipoResolucionNoVendible(r.tipo),
                        cantidad=_dec(r.cantidad), monto=r.monto, reclamo_id=r.reclamo_id, nota=r.nota,
                        usuario_id=r.usuario_id, usuario_nombre=nombres_usuarios.get(r.usuario_id),
                        created_at=r.created_at,
                    )
                    for r in row.resoluciones
                ]
            registros.append(registro)
        return registros


class SqlAlchemyReclamoProveedorRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, estado: str | None = None, proveedor_id: int | None = None) -> list[ReclamoProveedor]:
        condiciones = []
        if estado:
            condiciones.append(ReclamoProveedorModel.estado == estado)
        if proveedor_id is not None:
            condiciones.append(ReclamoProveedorModel.proveedor_id == proveedor_id)
        return self._consultar(*condiciones)

    def get_by_id(self, reclamo_id: int, bloquear: bool = False) -> ReclamoProveedor | None:
        if bloquear:
            if self._session.execute(
                select(ReclamoProveedorModel.id).where(ReclamoProveedorModel.id == reclamo_id).with_for_update()
            ).first() is None:
                return None
        reclamos = self._consultar(ReclamoProveedorModel.id == reclamo_id)
        return reclamos[0] if reclamos else None

    def add(self, reclamo: ReclamoProveedor) -> ReclamoProveedor:
        row = ReclamoProveedorModel(
            numero=reclamo.numero, proveedor_id=reclamo.proveedor_id, usuario_id=reclamo.usuario_id,
            proveedor_razon_social=reclamo.proveedor_razon_social, proveedor_ruc=reclamo.proveedor_ruc,
            proveedor_telefono=reclamo.proveedor_telefono, proveedor_email=reclamo.proveedor_email,
            proveedor_direccion=reclamo.proveedor_direccion, estado=reclamo.estado.value, notas=reclamo.notas,
            numero_nota_remision=reclamo.numero_nota_remision,
            items=[self._item_model(i) for i in reclamo.items],
        )
        self._session.add(row)
        self._session.flush()
        return self.get_by_id(row.id)

    def update(self, reclamo: ReclamoProveedor) -> ReclamoProveedor:
        row = self._session.get(ReclamoProveedorModel, reclamo.id, options=[selectinload(ReclamoProveedorModel.items)])
        for campo in (
            "notas", "respuesta_proveedor", "motivo_rechazo", "numero_nota_credito", "numero_nota_remision",
            "fecha_envio", "fecha_respuesta", "fecha_resolucion",
        ):
            setattr(row, campo, getattr(reclamo, campo))
        row.estado = reclamo.estado.value
        por_id = {i.id: i for i in reclamo.items}
        for item_row in row.items:
            item = por_id.get(item_row.id)
            if item is None:
                continue
            item_row.resolucion = item.resolucion.value if item.resolucion else None
            item_row.monto_nota_credito = item.monto_nota_credito or 0
            item_row.nota_resolucion = item.nota_resolucion
            item_row.resuelto_por = item.resuelto_por
            item_row.resuelto_at = item.resuelto_at
        self._session.flush()
        return self.get_by_id(reclamo.id)

    def replace_items(self, reclamo_id: int, items: list[ReclamoProveedorItem]) -> None:
        row = self._session.get(ReclamoProveedorModel, reclamo_id, options=[selectinload(ReclamoProveedorModel.items)])
        row.items.clear()
        self._session.flush()  # el UNIQUE (reclamo, registro) exige borrar antes de volver a insertar
        row.items.extend(self._item_model(i) for i in items)
        self._session.flush()

    def delete(self, reclamo_id: int) -> None:
        row = self._session.get(ReclamoProveedorModel, reclamo_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    def siguiente_numero(self) -> str:
        """RCL-AAAA-NNNN: el mayor número del año + 1, con un lock para que dos
        reclamos simultáneos no reciban el mismo."""
        self._session.execute(text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": _LOCK_NUMERO_RECLAMO})
        anio = int(self._session.execute(select(func.extract("year", func.current_date()))).scalar_one())
        prefijo = f"RCL-{anio}-"
        ultimo = self._session.execute(
            select(func.max(cast(func.substr(ReclamoProveedorModel.numero, len(prefijo) + 1), Integer)))
            .where(ReclamoProveedorModel.numero.like(f"{prefijo}%"))
        ).scalar()
        return f"{prefijo}{(ultimo or 0) + 1:04d}"

    @staticmethod
    def _item_model(item: ReclamoProveedorItem) -> ReclamoProveedorItemModel:
        return ReclamoProveedorItemModel(
            registro_id=item.registro_id, producto_id=item.producto_id, cantidad=item.cantidad,
            costo_unitario=item.costo_unitario, monto_nota_credito=item.monto_nota_credito or 0,
        )

    def _consultar(self, *condiciones) -> list[ReclamoProveedor]:
        stmt = (
            select(ReclamoProveedorModel, UsuarioModel.name)
            .outerjoin(UsuarioModel, UsuarioModel.id == ReclamoProveedorModel.usuario_id)
            .options(selectinload(ReclamoProveedorModel.items))
            .where(*condiciones)
            .order_by(ReclamoProveedorModel.created_at.desc(), ReclamoProveedorModel.id.desc())
        )
        filas = self._session.execute(stmt).all()
        registro_ids = {i.registro_id for row, _ in filas for i in row.items}
        datos: dict[int, tuple] = {}
        if registro_ids:
            registro = aliased(StockNoVendibleModel)
            datos = {
                rid: (codigo, nombre, unidad, motivo, nota)
                for rid, codigo, nombre, unidad, motivo, nota in self._session.execute(
                    select(registro.id, ProductoModel.codigo, ProductoModel.nombre, ProductoModel.unidad_medida,
                           registro.motivo, registro.nota)
                    .join(ProductoModel, ProductoModel.id == registro.producto_id)
                    .where(registro.id.in_(registro_ids))
                ).all()
            }
        reclamos = []
        for row, usuario in filas:
            items = []
            for i in row.items:
                codigo, nombre, unidad, motivo, nota = datos.get(i.registro_id, (None, None, None, None, None))
                items.append(ReclamoProveedorItem(
                    id=i.id, reclamo_id=i.reclamo_id, registro_id=i.registro_id, producto_id=i.producto_id,
                    cantidad=_dec(i.cantidad), costo_unitario=i.costo_unitario,
                    resolucion=ResolucionItemReclamo(i.resolucion) if i.resolucion else None,
                    monto_nota_credito=i.monto_nota_credito or 0, nota_resolucion=i.nota_resolucion,
                    resuelto_por=i.resuelto_por, resuelto_at=i.resuelto_at,
                    producto_codigo=codigo, producto_nombre=nombre, unidad_medida=unidad,
                    motivo=MotivoNoVendible(motivo) if motivo else None, nota_registro=nota,
                ))
            reclamos.append(ReclamoProveedor(
                id=row.id, numero=row.numero, proveedor_id=row.proveedor_id, usuario_id=row.usuario_id,
                proveedor_razon_social=row.proveedor_razon_social, proveedor_ruc=row.proveedor_ruc,
                proveedor_telefono=row.proveedor_telefono, proveedor_email=row.proveedor_email,
                proveedor_direccion=row.proveedor_direccion, estado=EstadoReclamoProveedor(row.estado),
                notas=row.notas, respuesta_proveedor=row.respuesta_proveedor, motivo_rechazo=row.motivo_rechazo,
                numero_nota_credito=row.numero_nota_credito, numero_nota_remision=row.numero_nota_remision,
                fecha_envio=row.fecha_envio, fecha_respuesta=row.fecha_respuesta,
                fecha_resolucion=row.fecha_resolucion, created_at=row.created_at, usuario_nombre=usuario,
                items=items,
            ))
        return reclamos

