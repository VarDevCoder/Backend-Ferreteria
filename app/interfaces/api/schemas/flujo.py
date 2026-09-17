"""Schemas del ciclo comercial: Pedido de Cliente, Solicitud de Presupuesto,
Orden de Compra y Orden de Envío."""
from datetime import date, datetime

from pydantic import BaseModel, Field


# --- Pedido de Cliente ------------------------------------------------------------

class ItemPedidoInput(BaseModel):
    producto_id: int
    cantidad: float = Field(gt=0)
    precio_unitario: int = Field(ge=0)


class PedidoClienteCreate(BaseModel):
    cliente_id: int | None = None
    cliente_nombre: str | None = None
    cliente_ruc: str | None = None
    cliente_telefono: str | None = None
    cliente_email: str | None = None
    cliente_direccion: str | None = None
    fecha_pedido: date | None = None
    fecha_entrega_solicitada: date | None = None
    descuento: int = Field(default=0, ge=0, le=100)
    notas: str | None = None
    items: list[ItemPedidoInput] = Field(min_length=1)


class PedidoClienteUpdate(BaseModel):
    cliente_id: int | None = None
    cliente_nombre: str
    cliente_ruc: str | None = None
    cliente_telefono: str | None = None
    cliente_email: str | None = None
    cliente_direccion: str | None = None
    fecha_entrega_solicitada: date | None = None
    descuento: int = Field(default=0, ge=0, le=100)
    notas: str | None = None
    items: list[ItemPedidoInput] = Field(min_length=1)


class ItemPedidoResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: float
    precio_unitario: int
    subtotal: int


class PedidoClienteResponse(BaseModel):
    id: int
    numero: str
    usuario_id: int
    cliente_id: int | None
    cliente_nombre: str
    cliente_ruc: str | None
    cliente_telefono: str | None
    cliente_email: str | None
    cliente_direccion: str | None
    fecha_pedido: date | None
    fecha_entrega_solicitada: date | None
    estado: str
    subtotal: int
    descuento: int
    total: int
    notas: str | None
    motivo_cancelacion: str | None
    created_at: datetime | None
    items: list[ItemPedidoResponse]

    @classmethod
    def desde_entidad(cls, p) -> "PedidoClienteResponse":
        return cls(
            id=p.id, numero=p.numero, usuario_id=p.usuario_id, cliente_id=p.cliente_id,
            cliente_nombre=p.cliente_nombre, cliente_ruc=p.cliente_ruc, cliente_telefono=p.cliente_telefono,
            cliente_email=p.cliente_email, cliente_direccion=p.cliente_direccion, fecha_pedido=p.fecha_pedido,
            fecha_entrega_solicitada=p.fecha_entrega_solicitada, estado=p.estado.value, subtotal=p.subtotal,
            descuento=p.descuento, total=p.total, notas=p.notas, motivo_cancelacion=p.motivo_cancelacion,
            created_at=p.created_at,
            items=[
                ItemPedidoResponse(id=i.id, producto_id=i.producto_id, cantidad=float(i.cantidad),
                                    precio_unitario=i.precio_unitario, subtotal=i.subtotal)
                for i in p.items
            ],
        )


# --- Solicitud de Presupuesto -------------------------------------------------------

class ItemSolicitudInput(BaseModel):
    producto_id: int
    cantidad_solicitada: float = Field(gt=0)


class SolicitudPresupuestoCreate(BaseModel):
    proveedor_id: int
    pedido_cliente_id: int | None = None
    fecha_limite_respuesta: date | None = None
    mensaje_solicitud: str | None = None
    items: list[ItemSolicitudInput] = Field(min_length=1)


class RespuestaItemInput(BaseModel):
    item_id: int
    tiene_stock: bool
    cantidad_disponible: float | None = None
    precio_unitario_cotizado: int | None = None


class CotizacionInput(BaseModel):
    proveedor_id: int
    dias_entrega_estimados: int = Field(gt=0)
    respuesta_proveedor: str | None = None
    items: list[RespuestaItemInput]


class SinStockInput(BaseModel):
    proveedor_id: int
    respuesta_proveedor: str = Field(min_length=1)


class VerSolicitudInput(BaseModel):
    proveedor_id: int


class ItemSolicitudResponse(BaseModel):
    id: int
    producto_id: int
    cantidad_solicitada: float
    tiene_stock: bool | None
    cantidad_disponible: float | None
    precio_unitario_cotizado: int | None
    subtotal_cotizado: int | None


class SolicitudPresupuestoResponse(BaseModel):
    id: int
    numero: str
    proveedor_id: int
    usuario_id: int
    pedido_cliente_id: int | None
    fecha_solicitud: date | None
    fecha_limite_respuesta: date | None
    fecha_respuesta: date | None
    estado: str
    mensaje_solicitud: str | None
    respuesta_proveedor: str | None
    total_cotizado: int | None
    dias_entrega_estimados: int | None
    created_at: datetime | None
    items: list[ItemSolicitudResponse]

    @classmethod
    def desde_entidad(cls, s) -> "SolicitudPresupuestoResponse":
        return cls(
            id=s.id, numero=s.numero, proveedor_id=s.proveedor_id, usuario_id=s.usuario_id,
            pedido_cliente_id=s.pedido_cliente_id, fecha_solicitud=s.fecha_solicitud,
            fecha_limite_respuesta=s.fecha_limite_respuesta, fecha_respuesta=s.fecha_respuesta,
            estado=s.estado.value, mensaje_solicitud=s.mensaje_solicitud,
            respuesta_proveedor=s.respuesta_proveedor, total_cotizado=s.total_cotizado,
            dias_entrega_estimados=s.dias_entrega_estimados, created_at=s.created_at,
            items=[
                ItemSolicitudResponse(
                    id=i.id, producto_id=i.producto_id, cantidad_solicitada=float(i.cantidad_solicitada),
                    tiene_stock=i.tiene_stock,
                    cantidad_disponible=float(i.cantidad_disponible) if i.cantidad_disponible is not None else None,
                    precio_unitario_cotizado=i.precio_unitario_cotizado, subtotal_cotizado=i.subtotal_cotizado,
                )
                for i in s.items
            ],
        )


# --- Orden de Compra ------------------------------------------------------------

class ItemOrdenCompraInput(BaseModel):
    producto_id: int
    cantidad_solicitada: float = Field(gt=0)
    precio_unitario: int = Field(ge=0)


class OrdenCompraCreate(BaseModel):
    pedido_cliente_id: int | None = None
    proveedor_nombre: str = Field(min_length=1, max_length=255)
    proveedor_ruc: str | None = None
    proveedor_telefono: str | None = None
    proveedor_email: str | None = None
    proveedor_direccion: str | None = None
    fecha_entrega_esperada: date | None = None
    descuento: int = Field(default=0, ge=0, le=100)
    notas: str | None = None
    items: list[ItemOrdenCompraInput] = Field(min_length=1)


class OrdenCompraUpdate(BaseModel):
    proveedor_nombre: str = Field(min_length=1, max_length=255)
    proveedor_ruc: str | None = None
    proveedor_telefono: str | None = None
    proveedor_email: str | None = None
    proveedor_direccion: str | None = None
    fecha_entrega_esperada: date | None = None
    descuento: int = Field(default=0, ge=0, le=100)
    notas: str | None = None
    items: list[ItemOrdenCompraInput] = Field(min_length=1)


class RecepcionMercaderiaInput(BaseModel):
    cantidades: dict[int, float] = Field(description="item_id -> cantidad recibida en este evento")


class ItemOrdenCompraResponse(BaseModel):
    id: int
    producto_id: int
    cantidad_solicitada: float
    cantidad_recibida: float
    precio_unitario: int
    subtotal: int


class OrdenCompraResponse(BaseModel):
    id: int
    numero: str
    usuario_id: int
    pedido_cliente_id: int | None
    proveedor_nombre: str
    proveedor_ruc: str | None
    proveedor_telefono: str | None
    proveedor_email: str | None
    proveedor_direccion: str | None
    fecha_orden: date | None
    fecha_entrega_esperada: date | None
    fecha_recepcion: date | None
    estado: str
    subtotal: int
    descuento: int
    total: int
    notas: str | None
    motivo_cancelacion: str | None
    created_at: datetime | None
    items: list[ItemOrdenCompraResponse]

    @classmethod
    def desde_entidad(cls, o) -> "OrdenCompraResponse":
        return cls(
            id=o.id, numero=o.numero, usuario_id=o.usuario_id, pedido_cliente_id=o.pedido_cliente_id,
            proveedor_nombre=o.proveedor_nombre, proveedor_ruc=o.proveedor_ruc,
            proveedor_telefono=o.proveedor_telefono, proveedor_email=o.proveedor_email,
            proveedor_direccion=o.proveedor_direccion, fecha_orden=o.fecha_orden,
            fecha_entrega_esperada=o.fecha_entrega_esperada, fecha_recepcion=o.fecha_recepcion,
            estado=o.estado.value, subtotal=o.subtotal, descuento=o.descuento, total=o.total, notas=o.notas,
            motivo_cancelacion=o.motivo_cancelacion, created_at=o.created_at,
            items=[
                ItemOrdenCompraResponse(
                    id=i.id, producto_id=i.producto_id, cantidad_solicitada=float(i.cantidad_solicitada),
                    cantidad_recibida=float(i.cantidad_recibida), precio_unitario=i.precio_unitario,
                    subtotal=i.subtotal,
                )
                for i in o.items
            ],
        )


# --- Orden de Envío ------------------------------------------------------------

class ItemOrdenEnvioInput(BaseModel):
    producto_id: int
    cantidad: float = Field(gt=0)


class OrdenEnvioCreate(BaseModel):
    pedido_cliente_id: int
    direccion_entrega: str = Field(min_length=1, max_length=500)
    contacto_entrega: str | None = None
    telefono_entrega: str | None = None
    metodo_envio: str | None = None
    transportista: str | None = None
    notas: str | None = None
    items: list[ItemOrdenEnvioInput] = Field(min_length=1)


class DespacharInput(BaseModel):
    numero_guia: str | None = None


class ItemOrdenEnvioResponse(BaseModel):
    id: int
    producto_id: int
    cantidad: float


class OrdenEnvioResponse(BaseModel):
    id: int
    numero: str
    usuario_id: int
    pedido_cliente_id: int
    direccion_entrega: str
    contacto_entrega: str | None
    telefono_entrega: str | None
    fecha_generacion: date | None
    fecha_envio: date | None
    fecha_entrega: date | None
    estado: str
    metodo_envio: str | None
    numero_guia: str | None
    transportista: str | None
    notas: str | None
    observaciones_entrega: str | None
    created_at: datetime | None
    items: list[ItemOrdenEnvioResponse]

    @classmethod
    def desde_entidad(cls, o) -> "OrdenEnvioResponse":
        return cls(
            id=o.id, numero=o.numero, usuario_id=o.usuario_id, pedido_cliente_id=o.pedido_cliente_id,
            direccion_entrega=o.direccion_entrega, contacto_entrega=o.contacto_entrega,
            telefono_entrega=o.telefono_entrega, fecha_generacion=o.fecha_generacion, fecha_envio=o.fecha_envio,
            fecha_entrega=o.fecha_entrega, estado=o.estado.value, metodo_envio=o.metodo_envio,
            numero_guia=o.numero_guia, transportista=o.transportista, notas=o.notas,
            observaciones_entrega=o.observaciones_entrega, created_at=o.created_at,
            items=[ItemOrdenEnvioResponse(id=i.id, producto_id=i.producto_id, cantidad=float(i.cantidad)) for i in o.items],
        )


# --- Comparación de ofertas (CU-13 ★) ------------------------------------------------

class OfertaCatalogoProveedor(BaseModel):
    proveedor_id: int
    proveedor_nombre: str
    precio: int
    disponible: bool
    tiempo_entrega_dias: int | None


class ComparacionProducto(BaseModel):
    producto_id: int
    producto_nombre: str
    cantidad_requerida: float
    ofertas_catalogo: list[OfertaCatalogoProveedor]


class ComparacionPedidoResponse(BaseModel):
    pedido: PedidoClienteResponse
    cotizaciones: list[SolicitudPresupuestoResponse]
    comparacion_catalogo: list[ComparacionProducto]
