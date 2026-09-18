"""Schemas de Caja y venta de mostrador."""
from datetime import datetime

from pydantic import BaseModel, Field


# --- Turno de caja -----------------------------------------------------------------

class AbrirCajaInput(BaseModel):
    fondo_inicial: int = Field(ge=0)


class MovimientoCajaInput(BaseModel):
    tipo: str
    monto: int = Field(gt=0)
    motivo: str | None = None


class CerrarCajaInput(BaseModel):
    conteo_fisico: int = Field(ge=0)
    notas: str | None = None


class MovimientoCajaResponse(BaseModel):
    id: int
    tipo: str
    monto: int
    motivo: str | None
    created_at: datetime | None


class CajaTurnoResponse(BaseModel):
    id: int
    usuario_id: int
    fondo_inicial: int
    estado: str
    fecha_apertura: datetime | None
    fecha_cierre: datetime | None
    total_ventas_efectivo: int
    total_ventas_tarjeta: int
    total_ventas_transferencia: int
    saldo_esperado: int
    conteo_fisico: int | None
    diferencia: int | None
    notas: str | None
    movimientos: list[MovimientoCajaResponse]

    @classmethod
    def desde_entidad(cls, t) -> "CajaTurnoResponse":
        return cls(
            id=t.id, usuario_id=t.usuario_id, fondo_inicial=t.fondo_inicial, estado=t.estado.value,
            fecha_apertura=t.fecha_apertura, fecha_cierre=t.fecha_cierre,
            total_ventas_efectivo=t.total_ventas_efectivo, total_ventas_tarjeta=t.total_ventas_tarjeta,
            total_ventas_transferencia=t.total_ventas_transferencia, saldo_esperado=t.saldo_esperado(),
            conteo_fisico=t.conteo_fisico, diferencia=t.diferencia, notas=t.notas,
            movimientos=[
                MovimientoCajaResponse(id=m.id, tipo=m.tipo.value, monto=m.monto, motivo=m.motivo, created_at=m.created_at)
                for m in t.movimientos
            ],
        )


# --- Venta de mostrador --------------------------------------------------------------

class ItemVentaInput(BaseModel):
    producto_id: int
    cantidad: float = Field(gt=0)
    precio_unitario: int | None = Field(default=None, ge=0)


class VentaMostradorCreate(BaseModel):
    cliente_id: int | None = None
    metodo_pago: str = "EFECTIVO"
    descuento: int = Field(default=0, ge=0, le=100)
    notas: str | None = None
    items: list[ItemVentaInput] = Field(min_length=1)


class ItemVentaResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: float
    precio_unitario: int
    subtotal: int


class VentaMostradorResponse(BaseModel):
    id: int
    numero: str
    caja_turno_id: int
    usuario_id: int
    cliente_id: int | None
    metodo_pago: str
    subtotal: int
    descuento: int
    total: int
    notas: str | None
    created_at: datetime | None
    items: list[ItemVentaResponse]

    @classmethod
    def desde_entidad(cls, v) -> "VentaMostradorResponse":
        return cls(
            id=v.id, numero=v.numero, caja_turno_id=v.caja_turno_id, usuario_id=v.usuario_id,
            cliente_id=v.cliente_id, metodo_pago=v.metodo_pago.value, subtotal=v.subtotal,
            descuento=v.descuento, total=v.total, notas=v.notas, created_at=v.created_at,
            items=[
                ItemVentaResponse(
                    id=i.id, producto_id=i.producto_id, cantidad=float(i.cantidad),
                    precio_unitario=i.precio_unitario, subtotal=i.subtotal,
                )
                for i in v.items
            ],
        )


class ResumenCajaHoyResponse(BaseModel):
    ventas_hoy: int
    total_hoy: int
