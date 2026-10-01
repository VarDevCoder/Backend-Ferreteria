"""Consultas de agregación para reportes de ventas. Solo lectura."""
from datetime import date, datetime, time, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.infrastructure.db.models import (
    PedidoClienteModel,
    ProductoModel,
    VentaMostradorItemModel,
    VentaMostradorModel,
)


def _rango(desde: date, hasta: date) -> tuple[datetime, datetime]:
    """[desde 00:00, hasta+1 00:00): incluye el día `hasta` completo."""
    return datetime.combine(desde, time.min), datetime.combine(hasta + timedelta(days=1), time.min)


class SqlAlchemyReporteRepository:
    def __init__(self, session: Session):
        self._session = session

    def ventas_por_metodo(self, desde: date, hasta: date) -> list[dict]:
        inicio, fin = _rango(desde, hasta)
        stmt = (
            select(VentaMostradorModel.metodo_pago, func.count(), func.coalesce(func.sum(VentaMostradorModel.total), 0))
            .where(VentaMostradorModel.created_at >= inicio, VentaMostradorModel.created_at < fin)
            .group_by(VentaMostradorModel.metodo_pago)
        )
        return [{"metodo_pago": m, "cantidad": c, "total": int(t)} for m, c, t in self._session.execute(stmt)]

    def ventas_por_dia(self, desde: date, hasta: date) -> list[dict]:
        inicio, fin = _rango(desde, hasta)
        dia = cast(VentaMostradorModel.created_at, Date)
        stmt = (
            select(dia, func.count(), func.coalesce(func.sum(VentaMostradorModel.total), 0))
            .where(VentaMostradorModel.created_at >= inicio, VentaMostradorModel.created_at < fin)
            .group_by(dia)
            .order_by(dia)
        )
        return [{"fecha": d, "cantidad": c, "total": int(t)} for d, c, t in self._session.execute(stmt)]

    def productos_mas_vendidos(self, desde: date, hasta: date, limite: int) -> list[dict]:
        """Ranking por importe vendido. El costo usa el precio de compra
        *actual* del producto, así que la utilidad es una estimación."""
        inicio, fin = _rango(desde, hasta)
        cantidad = func.sum(VentaMostradorItemModel.cantidad)
        importe = func.sum(VentaMostradorItemModel.subtotal)
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
