"""Casos de uso de consulta de inventario (CU-16 Kardex)."""
from app.domain.entities import MovimientoInventario, Producto
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
