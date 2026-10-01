from datetime import date

from pydantic import BaseModel


class ResumenMostrador(BaseModel):
    cantidad_ventas: int
    total: int
    ticket_promedio: int


class VentasPorMetodo(BaseModel):
    metodo_pago: str
    cantidad: int
    total: int


class VentasPorDia(BaseModel):
    fecha: date
    cantidad: int
    total: int


class ProductoVendido(BaseModel):
    producto_id: int
    codigo: str
    nombre: str
    cantidad: float
    total: int
    costo_estimado: int
    utilidad_estimada: int


class PedidosEntregados(BaseModel):
    cantidad: int
    total: int


class ReporteVentasResponse(BaseModel):
    desde: date
    hasta: date
    mostrador: ResumenMostrador
    por_metodo_pago: list[VentasPorMetodo]
    por_dia: list[VentasPorDia]
    productos_mas_vendidos: list[ProductoVendido]
    pedidos_entregados: PedidosEntregados
