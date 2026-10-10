"""Schemas de logística de pedidos: condiciones de entrega y pago, cobros,
rendiciones y hoja de entrega. Contrato: docs/api/logistica.md."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from .flujo import OrdenEnvioResponse, PedidoClienteResponse


class CondicionesPedidoInput(BaseModel):
    modalidad_entrega: str | None = Field(default=None, description="ENTREGA_DOMICILIO o RETIRA_CLIENTE")
    forma_pago: str | None = Field(default=None, description="ANTICIPADO, CONTRA_ENTREGA o CUENTA_CORRIENTE")


class PagoInput(BaseModel):
    metodo: str = Field(description="EFECTIVO, TARJETA_DEBITO, TARJETA_CREDITO, TRANSFERENCIA, QR, CHEQUE (y CUENTA_CORRIENTE solo al rendir)")
    monto: int = Field(gt=0)
    referencia: str | None = Field(default=None, max_length=100)


class RegistrarPagosInput(BaseModel):
    pagos: list[PagoInput] = Field(min_length=1)


class AnularPagoInput(BaseModel):
    motivo: str = Field(min_length=1, max_length=500)


class PagoPedidoResponse(BaseModel):
    id: int
    tipo: str
    metodo: str
    monto: int
    referencia: str | None
    caja_turno_id: int | None
    orden_envio_id: int | None
    usuario_id: int | None
    usuario_nombre: str | None
    created_at: datetime | None
    anulado: bool
    anulado_at: datetime | None
    anulado_por: int | None
    motivo_anulacion: str | None

    @classmethod
    def desde_entidad(cls, p) -> "PagoPedidoResponse":
        return cls(
            id=p.id, tipo=p.tipo.value, metodo=p.metodo.value, monto=p.monto, referencia=p.referencia,
            caja_turno_id=p.caja_turno_id, orden_envio_id=p.orden_envio_id, usuario_id=p.usuario_id,
            usuario_nombre=p.usuario_nombre, created_at=p.created_at, anulado=p.anulado, anulado_at=p.anulado_at,
            anulado_por=p.anulado_por, motivo_anulacion=p.motivo_anulacion,
        )


class CobrosPedidoResponse(BaseModel):
    pedido: PedidoClienteResponse
    pagos: list[PagoPedidoResponse]


class CobroPorRendirResponse(BaseModel):
    pedido_id: int
    numero: str
    cliente_id: int | None
    cliente_nombre: str
    cliente_telefono: str | None
    modalidad_entrega: str
    total: int
    monto_pagado: int
    por_rendir: int
    orden_envio_id: int | None
    orden_envio_numero: str | None
    fecha_entrega: date | None
    transportista: str | None
    conductor_nombre: str | None


# --- Hoja de entrega / remisión interna ------------------------------------------------

class EmpresaHoja(BaseModel):
    nombre_comercial: str
    razon_social: str | None
    ruc: str | None
    direccion: str | None
    ciudad: str | None
    telefono: str | None
    moneda_simbolo: str
    locale: str


class ItemHoja(BaseModel):
    producto_id: int
    codigo: str | None
    nombre: str
    unidad_medida: str | None
    cantidad: float


class CobroHoja(BaseModel):
    forma_pago: str | None
    estado_pago: str
    etiqueta: str
    total: int
    pagado: int
    a_cuenta: int
    a_cobrar_en_la_entrega: int


class HojaEnvioResponse(BaseModel):
    titulo: str
    leyenda: str
    empresa: EmpresaHoja | None
    orden: OrdenEnvioResponse
    pedido_numero: str | None
    cliente_nombre: str | None
    cliente_ruc: str | None
    cliente_telefono: str | None
    items: list[ItemHoja]
    cobro: CobroHoja | None

    @classmethod
    def desde(cls, datos: dict) -> "HojaEnvioResponse":
        empresa, orden, pedido, productos = datos["empresa"], datos["orden"], datos["pedido"], datos["productos"]
        retiro = orden.es_retiro()
        cobro = None
        if pedido is not None:
            # Contra entrega: lo que el repartidor (o el mostrador, en un retiro) tiene que cobrar.
            a_cobrar = pedido.saldo() if pedido.forma_pago and pedido.forma_pago.value == "CONTRA_ENTREGA" else 0
            cobro = CobroHoja(
                forma_pago=pedido.forma_pago.value if pedido.forma_pago else None, estado_pago=pedido.estado_pago.value,
                etiqueta=pedido.etiqueta_cobro(), total=pedido.total, pagado=pedido.monto_pagado,
                a_cuenta=pedido.monto_a_cuenta, a_cobrar_en_la_entrega=a_cobrar,
            )
        return cls(
            titulo=f"{'Retiro en el local' if retiro else 'Hoja de entrega'} — {orden.numero}",
            leyenda=(
                "Documento interno — no reemplaza a la factura ni a la nota de remisión timbrada"
                + (f" (N° {orden.numero_nota_remision})" if orden.numero_nota_remision else "")
            ),
            empresa=EmpresaHoja(
                nombre_comercial=empresa.nombre_comercial, razon_social=empresa.razon_social, ruc=empresa.ruc,
                direccion=empresa.direccion, ciudad=empresa.ciudad, telefono=empresa.telefono,
                moneda_simbolo=empresa.moneda_simbolo, locale=empresa.locale,
            ) if empresa else None,
            orden=OrdenEnvioResponse.desde_entidad(orden),
            pedido_numero=pedido.numero if pedido else None,
            cliente_nombre=pedido.cliente_nombre if pedido else None,
            cliente_ruc=pedido.cliente_ruc if pedido else None,
            cliente_telefono=pedido.cliente_telefono if pedido else None,
            items=[
                ItemHoja(
                    producto_id=i.producto_id,
                    codigo=productos[i.producto_id].codigo if productos.get(i.producto_id) else None,
                    nombre=productos[i.producto_id].nombre if productos.get(i.producto_id) else f"Producto #{i.producto_id}",
                    unidad_medida=productos[i.producto_id].unidad_medida if productos.get(i.producto_id) else None,
                    cantidad=float(i.cantidad),
                )
                for i in orden.items
            ],
            cobro=cobro,
        )
