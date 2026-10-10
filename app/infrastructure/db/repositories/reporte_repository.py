"""Consultas de agregación para reportes de ventas. Solo lectura."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.orm import Session

from app.core.tiempo import local_a_utc
from app.infrastructure.db.tiempo_sql import fecha_local

from app.infrastructure.db.models import (
    PedidoClienteModel,
    ProductoModel,
    VentaMostradorItemModel,
    VentaMostradorModel,
    VentaPagoModel,
)


def _rango(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """[desde 00:00, hasta+1 00:00) en la hora de la empresa, convertido a
    UTC (como se guarda `created_at`): incluye el día `hasta` completo."""
    return (
        local_a_utc(datetime.combine(desde, time.min)),
        local_a_utc(datetime.combine(hasta + timedelta(days=1), time.min)),
    )


class SqlAlchemyReporteRepository:
    def __init__(self, session: Session):
        self._session = session

    def ventas_por_metodo(self, desde: date, hasta: date) -> list[dict]:
        inicio, fin = _rango(desde, hasta)
        # Por cada pago, no por venta: una venta mixta suma a cada medio lo
        # que se cobró con él. La cantidad es de ventas en que se usó el medio.
        stmt = (
            select(VentaPagoModel.metodo, func.count(func.distinct(VentaPagoModel.venta_id)), func.coalesce(func.sum(VentaPagoModel.monto), 0))
            .join(VentaMostradorModel, VentaMostradorModel.id == VentaPagoModel.venta_id)
            .where(VentaMostradorModel.created_at >= inicio, VentaMostradorModel.created_at < fin)
            .group_by(VentaPagoModel.metodo)
            .order_by(func.sum(VentaPagoModel.monto).desc())
        )
        return [{"metodo_pago": m, "cantidad": c, "total": int(t)} for m, c, t in self._session.execute(stmt)]

    def ventas_por_dia(self, desde: date, hasta: date) -> list[dict]:
        inicio, fin = _rango(desde, hasta)
        dia = fecha_local(VentaMostradorModel.created_at)
        stmt = (
            select(dia, func.count(), func.coalesce(func.sum(VentaMostradorModel.total), 0))
            .where(VentaMostradorModel.created_at >= inicio, VentaMostradorModel.created_at < fin)
            .group_by(dia)
            .order_by(dia)
        )
        return [{"fecha": d, "cantidad": c, "total": int(t)} for d, c, t in self._session.execute(stmt)]

    def productos_mas_vendidos(self, desde: date, hasta: date, limite: int) -> list[dict]:
        """Ranking por importe cobrado. El descuento de la venta se reparte
        entre sus ítems en proporción a su subtotal (ítem × total / subtotal
        de la venta), así el ranking suma lo mismo que el total del período.
        El costo usa el precio de compra *actual* del producto, así que la
        utilidad es una estimación."""
        inicio, fin = _rango(desde, hasta)
        cantidad = func.sum(VentaMostradorItemModel.cantidad)
        neto_item = (
            cast(VentaMostradorItemModel.subtotal, Numeric) * VentaMostradorModel.total
            / func.nullif(VentaMostradorModel.subtotal, 0)
        )
        importe = func.round(func.coalesce(func.sum(neto_item), 0))
        stmt = (
            select(
                ProductoModel.id, ProductoModel.codigo, ProductoModel.nombre,
                cantidad, importe, ProductoModel.precio_compra,
            )
            .join(VentaMostradorItemModel, VentaMostradorItemModel.producto_id == ProductoModel.id)
            .join(VentaMostradorModel, VentaMostradorModel.id == VentaMostradorItemModel.venta_id)
            .where(VentaMostradorModel.created_at >= inicio, VentaMostradorModel.created_at < fin)
            .group_by(ProductoModel.id)
            .order_by(importe.desc())
            .limit(limite)
        )
        filas = []
        for pid, codigo, nombre, cant, total, costo_unitario in self._session.execute(stmt):
            costo = int(round(float(cant) * costo_unitario))
            filas.append({
                "producto_id": pid, "codigo": codigo, "nombre": nombre, "cantidad": float(cant),
                "total": int(total), "costo_estimado": costo, "utilidad_estimada": int(total) - costo,
            })
        return filas

    def pedidos_entregados(self, desde: date, hasta: date) -> dict:
        stmt = select(func.count(), func.coalesce(func.sum(PedidoClienteModel.total), 0)).where(
            PedidoClienteModel.estado == "ENTREGADO",
            PedidoClienteModel.fecha_pedido >= desde,
            PedidoClienteModel.fecha_pedido <= hasta,
        )
        cantidad, total = self._session.execute(stmt).one()
        return {"cantidad": cantidad, "total": int(total)}
