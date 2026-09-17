"""Repositorios de Categoría y Producto (el catálogo)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities import Categoria, Producto
from app.infrastructure.db.models import CategoriaModel, ProductoModel


class SqlAlchemyCategoriaRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, solo_activas: bool = False) -> list[Categoria]:
        stmt = select(CategoriaModel).order_by(CategoriaModel.orden, CategoriaModel.nombre)
        if solo_activas:
            stmt = stmt.where(CategoriaModel.activo.is_(True))
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, categoria_id: int) -> Categoria | None:
        row = self._session.get(CategoriaModel, categoria_id)
        return self._to_entity(row) if row else None

    def add(self, categoria: Categoria) -> Categoria:
        row = CategoriaModel(
            nombre=categoria.nombre,
            descripcion=categoria.descripcion,
            activo=categoria.activo,
            orden=categoria.orden,
        )
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, categoria: Categoria) -> Categoria:
        row = self._session.get(CategoriaModel, categoria.id)
        if row is None:
            raise ValueError(f"Categoria {categoria.id} no existe")
        row.nombre = categoria.nombre
        row.descripcion = categoria.descripcion
        row.activo = categoria.activo
        row.orden = categoria.orden
        self._session.flush()
        return self._to_entity(row)

    def delete(self, categoria_id: int) -> None:
        row = self._session.get(CategoriaModel, categoria_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    @staticmethod
    def _to_entity(row: CategoriaModel) -> Categoria:
        return Categoria(
            id=row.id, nombre=row.nombre, descripcion=row.descripcion, activo=row.activo, orden=row.orden
        )


class SqlAlchemyProductoRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(
        self, solo_activos: bool = False, categoria_id: int | None = None, busqueda: str | None = None
    ) -> list[Producto]:
        stmt = select(ProductoModel).order_by(ProductoModel.nombre)
        if solo_activos:
            stmt = stmt.where(ProductoModel.activo.is_(True))
        if categoria_id is not None:
            stmt = stmt.where(ProductoModel.categoria_id == categoria_id)
        if busqueda:
            patron = f"%{busqueda}%"
            stmt = stmt.where(ProductoModel.nombre.ilike(patron) | ProductoModel.codigo.ilike(patron))
        rows = self._session.execute(stmt).scalars().all()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, producto_id: int) -> Producto | None:
        row = self._session.get(ProductoModel, producto_id)
        return self._to_entity(row) if row else None

    def add(self, producto: Producto) -> Producto:
        row = self._to_model(producto)
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, producto: Producto) -> Producto:
        row = self._session.get(ProductoModel, producto.id)
        if row is None:
            raise ValueError(f"Producto {producto.id} no existe")
        row.categoria_id = producto.categoria_id
        row.codigo = producto.codigo
        row.nombre = producto.nombre
        row.descripcion = producto.descripcion
        row.precio_compra = producto.precio_compra
        row.precio_venta = producto.precio_venta
        row.stock_actual = producto.stock_actual
        row.stock_minimo = producto.stock_minimo
        row.unidad_medida = producto.unidad_medida
        row.activo = producto.activo
        self._session.flush()
        return self._to_entity(row)

    def delete(self, producto_id: int) -> None:
        row = self._session.get(ProductoModel, producto_id)
        if row:
            self._session.delete(row)
            self._session.flush()

    def siguiente_codigo(self) -> str:
        ultimo_id = self._session.execute(select(func.max(ProductoModel.id))).scalar() or 0
        return f"PROD-{ultimo_id + 1:05d}"

    @staticmethod
    def _to_entity(row: ProductoModel) -> Producto:
        return Producto(
            id=row.id,
            codigo=row.codigo,
            nombre=row.nombre,
            descripcion=row.descripcion,
            categoria_id=row.categoria_id,
            precio_compra=row.precio_compra,
            precio_venta=row.precio_venta,
            stock_actual=row.stock_actual,
            stock_minimo=row.stock_minimo,
            unidad_medida=row.unidad_medida,
            activo=row.activo,
        )

    @staticmethod
    def _to_model(producto: Producto) -> ProductoModel:
        return ProductoModel(
            id=producto.id,
            categoria_id=producto.categoria_id,
            codigo=producto.codigo,
            nombre=producto.nombre,
            descripcion=producto.descripcion,
            precio_compra=producto.precio_compra,
            precio_venta=producto.precio_venta,
            stock_actual=producto.stock_actual,
            stock_minimo=producto.stock_minimo,
            unidad_medida=producto.unidad_medida,
            activo=producto.activo,
        )
