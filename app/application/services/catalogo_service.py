"""Casos de uso del catálogo maestro: Categorías y Productos (CU-05, CU-06)."""
from decimal import Decimal

from app.domain.entities import Categoria, Producto
from app.domain.exceptions import RecursoNoEncontrado
from app.domain.repositories import CategoriaRepository, ProductoRepository

MARGEN_VENTA_PORCENTAJE = Decimal("25")


class CategoriaService:
    def __init__(self, categorias: CategoriaRepository):
        self._categorias = categorias

    def listar(self, solo_activas: bool = False) -> list[Categoria]:
        return self._categorias.list(solo_activas=solo_activas)

    def crear(self, nombre: str, descripcion: str | None, orden: int) -> Categoria:
        categoria = Categoria(id=None, nombre=nombre, descripcion=descripcion, orden=orden)
        return self._categorias.add(categoria)

    def actualizar(self, categoria_id: int, nombre: str, descripcion: str | None, activo: bool, orden: int) -> Categoria:
        actual = self._obtener(categoria_id)
        actual.nombre = nombre
        actual.descripcion = descripcion
        actual.activo = activo
        actual.orden = orden
        return self._categorias.update(actual)

    def eliminar(self, categoria_id: int) -> None:
        self._obtener(categoria_id)
        self._categorias.delete(categoria_id)

    def _obtener(self, categoria_id: int) -> Categoria:
        categoria = self._categorias.get_by_id(categoria_id)
        if categoria is None:
            raise RecursoNoEncontrado("Categoria", categoria_id)
        return categoria


class ProductoService:
    def __init__(self, productos: ProductoRepository):
        self._productos = productos

    def listar(
        self, solo_activos: bool = False, categoria_id: int | None = None, busqueda: str | None = None
    ) -> list[Producto]:
        return self._productos.list(solo_activos=solo_activos, categoria_id=categoria_id, busqueda=busqueda)

    def obtener(self, producto_id: int) -> Producto:
        producto = self._productos.get_by_id(producto_id)
        if producto is None:
            raise RecursoNoEncontrado("Producto", producto_id)
        return producto

    def crear(
        self,
        nombre: str,
        descripcion: str | None,
        categoria_id: int | None,
        precio_compra: int,
        precio_venta: int | None,
        stock_minimo: Decimal,
        unidad_medida: str,
        codigo: str | None = None,
    ) -> Producto:
        if precio_venta is None or precio_venta == 0:
            precio_venta = int(round(precio_compra * (1 + MARGEN_VENTA_PORCENTAJE / 100)))

        producto = Producto(
            id=None,
            codigo=codigo or self._productos.siguiente_codigo(),
            nombre=nombre,
            descripcion=descripcion,
            categoria_id=categoria_id,
            precio_compra=precio_compra,
            precio_venta=precio_venta,
            stock_actual=Decimal("0"),
            stock_minimo=stock_minimo,
            unidad_medida=unidad_medida,
        )
        return self._productos.add(producto)

    def actualizar(
        self,
        producto_id: int,
        nombre: str,
        descripcion: str | None,
        categoria_id: int | None,
        precio_compra: int,
        precio_venta: int,
        stock_minimo: Decimal,
        unidad_medida: str,
        activo: bool,
    ) -> Producto:
        actual = self.obtener(producto_id)
        actual.nombre = nombre
        actual.descripcion = descripcion
        actual.categoria_id = categoria_id
        actual.precio_compra = precio_compra
        actual.precio_venta = precio_venta
        actual.stock_minimo = stock_minimo
        actual.unidad_medida = unidad_medida
        actual.activo = activo
        return self._productos.update(actual)

    def eliminar(self, producto_id: int) -> None:
        self.obtener(producto_id)
        self._productos.delete(producto_id)
