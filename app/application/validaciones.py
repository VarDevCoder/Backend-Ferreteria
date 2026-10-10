"""Validaciones comunes de los ítems de un documento (venta, pedido, compra,
envío): que el producto exista, que esté activo cuando se vende o se pide y
que la cantidad respete su unidad (pz, caja... solo enteras)."""
from app.domain.entities import Producto
from app.domain.exceptions import RecursoNoEncontrado
from app.domain.repositories import ProductoRepository


def producto_existente(productos: ProductoRepository, producto_id: int) -> Producto:
    producto = productos.get_by_id(producto_id)
    if producto is None:
        raise RecursoNoEncontrado("Producto", producto_id)
    return producto


def validar_items(
    productos: ProductoRepository, items: list[dict], campo_cantidad: str = "cantidad", para_vender: bool = False,
) -> dict[int, Producto]:
    """Devuelve los productos de los ítems por id. Con `para_vender`, además
    rechaza productos desactivados."""
    encontrados: dict[int, Producto] = {}
    for item in items:
        producto = encontrados.get(item["producto_id"]) or producto_existente(productos, item["producto_id"])
        if para_vender:
            producto.validar_vendible()
        producto.validar_cantidad(item[campo_cantidad])
        encontrados[producto.id] = producto
    return encontrados
