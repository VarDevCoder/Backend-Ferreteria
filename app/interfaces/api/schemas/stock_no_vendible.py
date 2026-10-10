"""Schemas de stock no vendible y reclamos al proveedor."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

# --- Stock no vendible ----------------------------------------------------------------


class MarcarNoVendibleInput(BaseModel):
    producto_id: int
    cantidad: float = Field(gt=0, description="Unidades que pasan de vendible a no vendible")
    motivo: str = Field(description="AVERIADO, ABOLLADO, VENCIDO, DEFECTO_FABRICA u OTRO (este último exige nota)")
    nota: str | None = Field(default=None, max_length=1000)
    proveedor_id: int | None = Field(default=None, description="Proveedor al que se le podría reclamar")
    orden_compra_id: int | None = Field(default=None, description="Orden de compra con la que llegó (opcional)")


class ResolverNoVendibleInput(BaseModel):
    cantidad: float | None = Field(default=None, gt=0, description="Vacío = todas las unidades libres del registro")
    nota: str | None = Field(default=None, max_length=1000)


class ResolucionNoVendibleResponse(BaseModel):
    id: int
    tipo: str
    cantidad: float
    monto: int
    reclamo_id: int | None
    nota: str | None
    usuario_id: int | None
    usuario_nombre: str | None
    created_at: datetime | None


class StockNoVendibleResponse(BaseModel):
    id: int
    producto_id: int
    producto_codigo: str | None
    producto_nombre: str | None
    unidad_medida: str | None
    cantidad: float
    cantidad_pendiente: float
    cantidad_en_reclamo: float
    cantidad_libre: float
    motivo: str
    nota: str | None
    proveedor_id: int | None
    proveedor_nombre: str | None
    orden_compra_id: int | None
    costo_unitario: int
    valor_pendiente: int
    estado: str
    usuario_id: int | None
    usuario_nombre: str | None
    created_at: datetime | None
    updated_at: datetime | None
    resoluciones: list[ResolucionNoVendibleResponse] | None = None

    @classmethod
    def desde_entidad(cls, r, con_resoluciones: bool = False) -> "StockNoVendibleResponse":
        return cls(
            id=r.id, producto_id=r.producto_id, producto_codigo=r.producto_codigo, producto_nombre=r.producto_nombre,
            unidad_medida=r.unidad_medida, cantidad=float(r.cantidad), cantidad_pendiente=float(r.cantidad_pendiente),
            cantidad_en_reclamo=float(r.cantidad_en_reclamo), cantidad_libre=float(r.cantidad_libre()),
            motivo=r.motivo.value, nota=r.nota, proveedor_id=r.proveedor_id, proveedor_nombre=r.proveedor_nombre,
            orden_compra_id=r.orden_compra_id, costo_unitario=r.costo_unitario, valor_pendiente=r.valor_pendiente(),
            estado=r.estado.value, usuario_id=r.usuario_id, usuario_nombre=r.usuario_nombre,
            created_at=r.created_at, updated_at=r.updated_at,
            resoluciones=[
                ResolucionNoVendibleResponse(
                    id=x.id, tipo=x.tipo.value, cantidad=float(x.cantidad), monto=x.monto, reclamo_id=x.reclamo_id,
                    nota=x.nota, usuario_id=x.usuario_id, usuario_nombre=x.usuario_nombre, created_at=x.created_at,
                )
                for x in r.resoluciones
            ] if con_resoluciones else None,
        )


# --- Reclamos al proveedor --------------------------------------------------------------


class ItemReclamoInput(BaseModel):
    registro_id: int = Field(description="Registro de stock no vendible")
    cantidad: float | None = Field(default=None, gt=0, description="Vacío = todas las unidades libres del registro")


class ReclamoCreate(BaseModel):
    proveedor_id: int
    notas: str | None = Field(default=None, max_length=2000)
    items: list[ItemReclamoInput] = Field(min_length=1)


class ReclamoUpdate(BaseModel):
    notas: str | None = Field(default=None, max_length=2000)
    items: list[ItemReclamoInput] = Field(min_length=1)


class EnviarReclamoInput(BaseModel):
    numero_nota_remision: str | None = Field(default=None, max_length=50, description="Si la mercadería viaja al proveedor")


class AceptarReclamoInput(BaseModel):
    respuesta_proveedor: str | None = Field(default=None, max_length=2000)


class RechazarReclamoInput(BaseModel):
    motivo: str = Field(min_length=1, max_length=2000)


class ResolverItemInput(BaseModel):
    resolucion: str = Field(description="REPOSICION, NOTA_CREDITO o RECHAZADO")
    monto_nota_credito: int | None = Field(default=None, gt=0, description="Obligatorio con NOTA_CREDITO")
    numero_nota_credito: str | None = Field(default=None, max_length=50, description="N° de la nota de crédito del proveedor")
    nota: str | None = Field(default=None, max_length=1000)


class DocumentosReclamoInput(BaseModel):
    numero_nota_credito: str | None = Field(default=None, max_length=50)
    numero_nota_remision: str | None = Field(default=None, max_length=50)


class ItemReclamoResponse(BaseModel):
    id: int
    registro_id: int
    producto_id: int
    producto_codigo: str | None
    producto_nombre: str | None
    unidad_medida: str | None
    motivo: str | None
    nota_registro: str | None
    cantidad: float
    costo_unitario: int
    subtotal: int
    resolucion: str | None
    monto_nota_credito: int
    nota_resolucion: str | None
    resuelto_por: int | None
    resuelto_at: datetime | None


class ProveedorReclamo(BaseModel):
    id: int | None
    razon_social: str
    ruc: str | None
    telefono: str | None
    email: str | None
    direccion: str | None


class ReclamoResponse(BaseModel):
    id: int
    numero: str
    estado: str
    proveedor: ProveedorReclamo
    usuario_id: int | None
    usuario_nombre: str | None
    notas: str | None
    respuesta_proveedor: str | None
    motivo_rechazo: str | None
    numero_nota_credito: str | None
    numero_nota_remision: str | None
    fecha_envio: datetime | None
    fecha_respuesta: datetime | None
    fecha_resolucion: datetime | None
    created_at: datetime | None
    cantidad_items: int
    items_pendientes: int
    total_reclamado: int
    total_nota_credito: int
    items: list[ItemReclamoResponse]

    @classmethod
    def desde_entidad(cls, r) -> "ReclamoResponse":
        return cls(
            id=r.id, numero=r.numero, estado=r.estado.value,
            proveedor=ProveedorReclamo(
                id=r.proveedor_id, razon_social=r.proveedor_razon_social, ruc=r.proveedor_ruc,
                telefono=r.proveedor_telefono, email=r.proveedor_email, direccion=r.proveedor_direccion,
            ),
            usuario_id=r.usuario_id, usuario_nombre=r.usuario_nombre, notas=r.notas,
            respuesta_proveedor=r.respuesta_proveedor, motivo_rechazo=r.motivo_rechazo,
            numero_nota_credito=r.numero_nota_credito, numero_nota_remision=r.numero_nota_remision,
            fecha_envio=r.fecha_envio, fecha_respuesta=r.fecha_respuesta, fecha_resolucion=r.fecha_resolucion,
            created_at=r.created_at, cantidad_items=len(r.items),
            items_pendientes=sum(1 for i in r.items if not i.esta_resuelto()),
            total_reclamado=r.total_reclamado(), total_nota_credito=r.total_nota_credito(),
            items=[
                ItemReclamoResponse(
                    id=i.id, registro_id=i.registro_id, producto_id=i.producto_id, producto_codigo=i.producto_codigo,
                    producto_nombre=i.producto_nombre, unidad_medida=i.unidad_medida,
                    motivo=i.motivo.value if i.motivo else None, nota_registro=i.nota_registro,
                    cantidad=float(i.cantidad), costo_unitario=i.costo_unitario, subtotal=i.subtotal(),
                    resolucion=i.resolucion.value if i.resolucion else None, monto_nota_credito=i.monto_nota_credito,
                    nota_resolucion=i.nota_resolucion, resuelto_por=i.resuelto_por, resuelto_at=i.resuelto_at,
                )
                for i in r.items
            ],
        )


class EmpresaDocumento(BaseModel):
    nombre_comercial: str
    razon_social: str | None
    ruc: str | None
    direccion: str | None
    ciudad: str | None
    telefono: str | None
    email: str | None
    moneda_simbolo: str
    locale: str


class DocumentoReclamoResponse(BaseModel):
    """Todo lo necesario para imprimir o mandar el reclamo al proveedor."""

    titulo: str
    leyenda: str
    empresa: EmpresaDocumento
    reclamo: ReclamoResponse

    @classmethod
    def desde(cls, empresa, reclamo) -> "DocumentoReclamoResponse":
        return cls(
            titulo=f"Reclamo al proveedor N° {reclamo.numero}",
            leyenda="Documento interno de reclamo — no válido como comprobante fiscal",
            empresa=EmpresaDocumento(
                nombre_comercial=empresa.nombre_comercial, razon_social=empresa.razon_social, ruc=empresa.ruc,
                direccion=empresa.direccion, ciudad=empresa.ciudad, telefono=empresa.telefono, email=empresa.email,
                moneda_simbolo=empresa.moneda_simbolo, locale=empresa.locale,
            ),
            reclamo=ReclamoResponse.desde_entidad(reclamo),
        )
