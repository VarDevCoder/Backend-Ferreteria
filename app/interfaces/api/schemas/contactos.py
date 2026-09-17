from pydantic import BaseModel, Field


class ClienteCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    ruc: str | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    notas: str | None = None


class ClienteUpdate(ClienteCreate):
    activo: bool = True


class ClienteResponse(BaseModel):
    id: int
    nombre: str
    ruc: str | None
    telefono: str | None
    email: str | None
    direccion: str | None
    ciudad: str | None
    activo: bool
    notas: str | None


class ProveedorCreate(BaseModel):
    razon_social: str = Field(min_length=1, max_length=255)
    ruc: str = Field(min_length=1, max_length=50)
    email: str
    password: str = Field(min_length=8)
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    rubros: str | None = None
    notas: str | None = None


class ProveedorUpdate(BaseModel):
    razon_social: str = Field(min_length=1, max_length=255)
    ruc: str = Field(min_length=1, max_length=50)
    telefono: str | None = None
    direccion: str | None = None
    ciudad: str | None = None
    rubros: str | None = None
    notas: str | None = None


class ProveedorResponse(BaseModel):
    id: int
    razon_social: str
    ruc: str
    telefono: str | None
    direccion: str | None
    ciudad: str | None
    rubros: str | None
    notas: str | None
    email: str | None
    activo: bool


class ProveedorProductoCreate(BaseModel):
    proveedor_id: int
    producto_id: int
    precio: int = Field(ge=0)
    codigo_proveedor: str | None = None
    nombre_proveedor: str | None = None
    tiempo_entrega_dias: int | None = Field(default=None, ge=0)
    notas: str | None = None


class ProveedorProductoUpdate(BaseModel):
    precio: int = Field(ge=0)
    codigo_proveedor: str | None = None
    nombre_proveedor: str | None = None
    disponible: bool = True
    tiempo_entrega_dias: int | None = Field(default=None, ge=0)
    notas: str | None = None


class ProveedorProductoResponse(BaseModel):
    id: int
    proveedor_id: int
    producto_id: int
    codigo_proveedor: str | None
    nombre_proveedor: str | None
    precio: int
    disponible: bool
    tiempo_entrega_dias: int | None
    notas: str | None
