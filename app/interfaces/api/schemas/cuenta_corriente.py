"""Schemas de cuenta corriente de clientes (ventas a cuenta y cobros)."""
from datetime import datetime

from pydantic import BaseModel, Field


class MovimientoCuentaResponse(BaseModel):
    id: int
    tipo: str
    monto: int
    venta_id: int | None
    metodo_pago: str | None
    referencia: str | None
    created_at: datetime | None


class EstadoDeCuentaResponse(BaseModel):
    cliente_id: int
    nombre: str
    limite_credito: int
    saldo: int
    disponible: int
    movimientos: list[MovimientoCuentaResponse]


class CobroInput(BaseModel):
    monto: int = Field(gt=0)
    metodo: str = "EFECTIVO"
    referencia: str | None = Field(default=None, max_length=200)


class DeudorResponse(BaseModel):
    cliente_id: int
    nombre: str
    ruc: str | None
    telefono: str | None
    limite_credito: int
    saldo: int
    deuda_desde: datetime | None
    dias_de_atraso: int
    ultimo_pago: datetime | None
    hasta_30: int
    de_31_a_60: int
    de_61_a_90: int
    mas_de_90: int
