"""Reporte de ventas por período: totales, medios de pago, evolución diaria
y productos más vendidos."""
from datetime import date, timedelta

from app.domain.exceptions import SolicitudInvalida

MAX_DIAS = 366


class ReporteService:
    def __init__(self, reportes):
        self._reportes = reportes

    def ventas(self, desde: date | None, hasta: date | None, limite_productos: int = 10) -> dict:
        hasta = hasta or date.today()
        desde = desde or hasta.replace(day=1)
        if desde > hasta:
            raise SolicitudInvalida("La fecha 'desde' no puede ser posterior a 'hasta'")
        if hasta - desde > timedelta(days=MAX_DIAS):
            raise SolicitudInvalida(f"El período no puede superar {MAX_DIAS} días")

        por_metodo = self._reportes.ventas_por_metodo(desde, hasta)
        cantidad = sum(m["cantidad"] for m in por_metodo)
        total = sum(m["total"] for m in por_metodo)
        productos = self._reportes.productos_mas_vendidos(desde, hasta, limite_productos)
        return {
            "desde": desde,
            "hasta": hasta,
            "mostrador": {
                "cantidad_ventas": cantidad,
                "total": total,
                "ticket_promedio": int(round(total / cantidad)) if cantidad else 0,
            },
            "por_metodo_pago": por_metodo,
            "por_dia": self._reportes.ventas_por_dia(desde, hasta),
            "productos_mas_vendidos": productos,
            "pedidos_entregados": self._reportes.pedidos_entregados(desde, hasta),
        }
