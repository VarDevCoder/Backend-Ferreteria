"""Repositorios de Cliente, Proveedor y su catálogo de productos ofrecidos."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.infrastructure.db.repositories.catalogo_repository import patron_like, sin_tildes_sql
from app.domain.entities import Cliente, Proveedor, ProveedorProducto
from app.infrastructure.db.models import (
    ClienteModel,
    MovimientoCuentaCorrienteModel,
    OrdenCompraModel,
    PedidoClienteModel,
    ProveedorModel,
    ProveedorProductoModel,
)


class SqlAlchemyClienteRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(
        self, busqueda: str | None = None, activo: bool | None = None, ciudad: str | None = None
    ) -> list[Cliente]:
        stmt = select(ClienteModel).order_by(ClienteModel.nombre)
        if busqueda:
            # Sin importar tildes ni mayúsculas ("benitez" encuentra "Benítez").
            patron = patron_like(busqueda.strip())
            stmt = stmt.where(
                sin_tildes_sql(ClienteModel.nombre).like(patron, escape="\\")
                | sin_tildes_sql(ClienteModel.ruc).like(patron, escape="\\")
                | sin_tildes_sql(ClienteModel.email).like(patron, escape="\\")
                | sin_tildes_sql(ClienteModel.telefono).like(patron, escape="\\")
            )
        if activo is not None:
            stmt = stmt.where(ClienteModel.activo.is_(activo))
        if ciudad:
            stmt = stmt.where(ClienteModel.ciudad == ciudad)
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, cliente_id: int) -> Cliente | None:
        row = self._session.get(ClienteModel, cliente_id)
        return self._to_entity(row) if row else None

    def add(self, cliente: Cliente) -> Cliente:
        row = self._to_model(cliente)
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, cliente: Cliente) -> Cliente:
        row = self._session.get(ClienteModel, cliente.id)
        if row is None:
            raise ValueError(f"Cliente {cliente.id} no existe")
        row.nombre = cliente.nombre
        row.ruc = cliente.ruc
        row.telefono = cliente.telefono
        row.email = cliente.email
        row.direccion = cliente.direccion
        row.ciudad = cliente.ciudad
        row.activo = cliente.activo
        row.notas = cliente.notas
        row.limite_credito = cliente.limite_credito
        self._session.flush()
        return self._to_entity(row)

    def delete(self, cliente_id: int) -> None:
        row = self._session.get(ClienteModel, cliente_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    def tiene_pedidos(self, cliente_id: int) -> bool:
        """Pedidos o cuenta corriente: en ambos casos el historial obliga a desactivarlo en vez de borrarlo."""
        stmt = select(PedidoClienteModel.id).where(PedidoClienteModel.cliente_id == cliente_id).limit(1)
        cuenta = select(MovimientoCuentaCorrienteModel.id).where(MovimientoCuentaCorrienteModel.cliente_id == cliente_id).limit(1)
        return self._session.execute(stmt).first() is not None or self._session.execute(cuenta).first() is not None

    def existe_ruc(self, ruc: str, excluir_id: int | None = None) -> bool:
        return self._existe(func.lower(ClienteModel.ruc) == ruc.lower(), excluir_id)

    def existe_email(self, email: str, excluir_id: int | None = None) -> bool:
        return self._existe(func.lower(ClienteModel.email) == email.lower(), excluir_id)

    def _existe(self, condicion, excluir_id: int | None) -> bool:
        stmt = select(ClienteModel.id).where(condicion)
        if excluir_id is not None:
            stmt = stmt.where(ClienteModel.id != excluir_id)
        return self._session.execute(stmt.limit(1)).first() is not None

    def ciudades(self) -> list[str]:
        stmt = select(ClienteModel.ciudad).where(ClienteModel.ciudad.is_not(None)).distinct()
        return sorted({c for c in self._session.execute(stmt).scalars().all() if c})

    @staticmethod
    def _to_entity(row: ClienteModel) -> Cliente:
        return Cliente(
            id=row.id,
            nombre=row.nombre,
            ruc=row.ruc,
            telefono=row.telefono,
            email=row.email,
            direccion=row.direccion,
            ciudad=row.ciudad,
            activo=row.activo,
            notas=row.notas,
            limite_credito=row.limite_credito or 0,
        )

    @staticmethod
    def _to_model(cliente: Cliente) -> ClienteModel:
        return ClienteModel(
            id=cliente.id,
            nombre=cliente.nombre,
            ruc=cliente.ruc,
            telefono=cliente.telefono,
            email=cliente.email,
            direccion=cliente.direccion,
            ciudad=cliente.ciudad,
            activo=cliente.activo,
            notas=cliente.notas,
            limite_credito=cliente.limite_credito,
        )


class SqlAlchemyProveedorRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, solo_activos: bool = False) -> list[Proveedor]:
        stmt = select(ProveedorModel).options(joinedload(ProveedorModel.user)).order_by(ProveedorModel.razon_social)
        if solo_activos:
            stmt = stmt.join(ProveedorModel.user).where(ProveedorModel.user.has(activo=True))
        rows = self._session.execute(stmt).unique().scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, proveedor_id: int) -> Proveedor | None:
        row = self._session.get(ProveedorModel, proveedor_id, options=[joinedload(ProveedorModel.user)])
        return self._to_entity(row) if row else None

    def existe_ruc(self, ruc: str, excluir_id: int | None = None) -> bool:
        stmt = select(ProveedorModel.id).where(func.lower(ProveedorModel.ruc) == ruc.lower())
        if excluir_id is not None:
            stmt = stmt.where(ProveedorModel.id != excluir_id)
        return self._session.execute(stmt.limit(1)).first() is not None

    def get_by_user_id(self, user_id: int) -> Proveedor | None:
        stmt = (
            select(ProveedorModel)
            .options(joinedload(ProveedorModel.user))
            .where(ProveedorModel.user_id == user_id)
        )
        row = self._session.execute(stmt).unique().scalar_one_or_none()
        return self._to_entity(row) if row else None

    def add(self, proveedor: Proveedor) -> Proveedor:
        row = ProveedorModel(
            user_id=proveedor.user_id,
            razon_social=proveedor.razon_social,
            ruc=proveedor.ruc,
            telefono=proveedor.telefono,
            direccion=proveedor.direccion,
            ciudad=proveedor.ciudad,
            rubros=proveedor.rubros,
            notas=proveedor.notas,
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row, attribute_names=["user"])
        return self._to_entity(row)

    def update(self, proveedor: Proveedor) -> Proveedor:
        row = self._session.get(ProveedorModel, proveedor.id, options=[joinedload(ProveedorModel.user)])
        if row is None:
            raise ValueError(f"Proveedor {proveedor.id} no existe")
        row.razon_social = proveedor.razon_social
        row.ruc = proveedor.ruc
        row.telefono = proveedor.telefono
        row.direccion = proveedor.direccion
        row.ciudad = proveedor.ciudad
        row.rubros = proveedor.rubros
        row.notas = proveedor.notas
        self._session.flush()
        return self._to_entity(row)

    def delete(self, proveedor_id: int) -> None:
        row = self._session.get(ProveedorModel, proveedor_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    @staticmethod
    def _to_entity(row: ProveedorModel) -> Proveedor:
        return Proveedor(
            id=row.id,
            user_id=row.user_id,
            razon_social=row.razon_social,
            ruc=row.ruc,
            telefono=row.telefono,
            direccion=row.direccion,
            ciudad=row.ciudad,
            rubros=row.rubros,
            notas=row.notas,
            email=row.user.email if row.user else None,
            usuario_activo=row.user.activo if row.user else True,
        )


class SqlAlchemyProveedorProductoRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(
        self, proveedor_id: int | None = None, producto_id: int | None = None, disponible: bool | None = None
    ) -> list[ProveedorProducto]:
        stmt = select(ProveedorProductoModel)
        if proveedor_id is not None:
            stmt = stmt.where(ProveedorProductoModel.proveedor_id == proveedor_id)
        if producto_id is not None:
            stmt = stmt.where(ProveedorProductoModel.producto_id == producto_id)
        if disponible is not None:
            stmt = stmt.where(ProveedorProductoModel.disponible.is_(disponible))
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, item_id: int) -> ProveedorProducto | None:
        row = self._session.get(ProveedorProductoModel, item_id)
        return self._to_entity(row) if row else None

    def existe(self, proveedor_id: int, producto_id: int) -> bool:
        stmt = select(ProveedorProductoModel.id).where(
            ProveedorProductoModel.proveedor_id == proveedor_id,
            ProveedorProductoModel.producto_id == producto_id,
        )
        return self._session.execute(stmt).first() is not None

    def add(self, item: ProveedorProducto) -> ProveedorProducto:
        row = self._to_model(item)
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, item: ProveedorProducto) -> ProveedorProducto:
        row = self._session.get(ProveedorProductoModel, item.id)
        if row is None:
            raise ValueError(f"ProveedorProducto {item.id} no existe")
        row.codigo_proveedor = item.codigo_proveedor
        row.nombre_proveedor = item.nombre_proveedor
        row.precio = item.precio
        row.disponible = item.disponible
        row.tiempo_entrega_dias = item.tiempo_entrega_dias
        row.notas = item.notas
        self._session.flush()
        return self._to_entity(row)

    def delete(self, item_id: int) -> None:
        row = self._session.get(ProveedorProductoModel, item_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    @staticmethod
    def _to_entity(row: ProveedorProductoModel) -> ProveedorProducto:
        return ProveedorProducto(
            id=row.id,
            proveedor_id=row.proveedor_id,
            producto_id=row.producto_id,
            codigo_proveedor=row.codigo_proveedor,
            nombre_proveedor=row.nombre_proveedor,
            precio=row.precio,
            disponible=row.disponible,
            tiempo_entrega_dias=row.tiempo_entrega_dias,
            notas=row.notas,
        )

    @staticmethod
    def _to_model(item: ProveedorProducto) -> ProveedorProductoModel:
        return ProveedorProductoModel(
            id=item.id,
            proveedor_id=item.proveedor_id,
            producto_id=item.producto_id,
            codigo_proveedor=item.codigo_proveedor,
            nombre_proveedor=item.nombre_proveedor,
            precio=item.precio,
            disponible=item.disponible,
            tiempo_entrega_dias=item.tiempo_entrega_dias,
            notas=item.notas,
        )
