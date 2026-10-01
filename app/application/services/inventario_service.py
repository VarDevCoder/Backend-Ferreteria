"""Casos de uso de inventario: consulta de stock, kardex (CU-16) y ajustes
manuales (carga de inventario inicial, conteo físico, roturas)."""
from decimal import Decimal

from app.domain.entities import MovimientoInventario, Producto
from app.domain.enums import TipoMovimientoInventario, TipoReferenciaMovimiento
from app.domain.exceptions import RecursoNoEncontrado, SolicitudInvalida
from app.domain.repositories import MovimientoInventarioRepository, ProductoRepository


class InventarioService:
    def __init__(self, productos: ProductoRepository, movimientos: MovimientoInventarioRepository):
        self._productos = productos
        self._movimientos = movimientos

    def listar_stock(self, solo_bajo_stock: bool = False) -> list[Producto]:
        productos = self._productos.list(solo_activos=True)
        if solo_bajo_stock:
            productos = [p for p in productos if p.tiene_stock_bajo()]
        return productos

    def movimientos_recientes(self, producto_id: int | None = None, tipo: str | None = None, limit: int = 100) -> list[MovimientoInventario]:
        return self._movimientos.list(producto_id=producto_id, tipo=tipo, limit=limit)

    def kardex(self, producto_id: int) -> list[MovimientoInventario]:
        return self._movimientos.list(producto_id=producto_id)

    def ajustar_stock(self, producto_id: int, stock_nuevo: Decimal, motivo: str, usuario_id: int) -> MovimientoInventario:
        """Fija el stock de un producto al valor contado y deja el ajuste en
        el kardex. `cantidad` queda con signo: positiva si sumó, negativa si
        restó, para que el historial explique la diferencia."""
        producto = self._productos.get_by_id(producto_id)
        if producto is None:
            raise RecursoNoEncontrado("Producto", producto_id)
        stock_nuevo = Decimal(str(stock_nuevo))
        if stock_nuevo < 0:
            raise SolicitudInvalida("El stock no puede ser negativo")
        if not motivo or not motivo.strip():
            raise SolicitudInvalida("Indicá el motivo del ajuste")
        stock_anterior = producto.stock_actual
        diferencia = stock_nuevo - stock_anterior
        if diferencia == 0:
            raise SolicitudInvalida("El stock indicado es igual al actual: no hay nada que ajustar")

        producto.stock_actual = stock_nuevo
        self._productos.update(producto)
        return self._movimientos.add(
            MovimientoInventario(
                id=None, producto_id=producto.id, tipo=TipoMovimientoInventario.AJUSTE,
                cantidad=diferencia, stock_anterior=stock_anterior, stock_nuevo=stock_nuevo,
                referencia_tipo=TipoReferenciaMovimiento.AJUSTE_MANUAL, referencia_id=producto.id,
                usuario_id=usuario_id, observaciones=motivo.strip(),
            )
        )
