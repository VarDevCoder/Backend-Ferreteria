from datetime import datetime

from pydantic import BaseModel, Field

from .catalogo import ProductoResponse


class MovimientoInventarioResponse(BaseModel):
    id: int
    producto_id: int
    tipo: str
    cantidad: float
    stock_anterior: float
    stock_nuevo: float
    referencia_tipo: str
    referencia_id: int
    usuario_id: int | None
    observaciones: str | None
    created_at: datetime | None
    # Solo en movimientos que tocan el stock no vendible (null en el resto).
    no_vendible_anterior: float | None = None
    no_vendible_nuevo: float | None = None

    @classmethod
    def desde_entidad(cls, m) -> "MovimientoInventarioResponse":
        return cls(
            id=m.id, producto_id=m.producto_id, tipo=m.tipo.value, cantidad=float(m.cantidad),
            stock_anterior=float(m.stock_anterior), stock_nuevo=float(m.stock_nuevo),
            referencia_tipo=m.referencia_tipo.value, referencia_id=m.referencia_id, usuario_id=m.usuario_id,
            observaciones=m.observaciones, created_at=m.created_at,
            no_vendible_anterior=float(m.no_vendible_anterior) if m.no_vendible_anterior is not None else None,
            no_vendible_nuevo=float(m.no_vendible_nuevo) if m.no_vendible_nuevo is not None else None,
        )


class AjusteStockInput(BaseModel):
    producto_id: int
    stock_nuevo: float = Field(ge=0, description="Stock real contado; el sistema calcula la diferencia")
    motivo: str = Field(min_length=1, max_length=500, description="Ej. inventario inicial, conteo físico, rotura")


__all__ = ["AjusteStockInput", "MovimientoInventarioResponse", "ProductoResponse"]
