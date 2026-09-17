from pydantic import BaseModel, Field


class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = None
    orden: int = 0


class CategoriaUpdate(CategoriaCreate):
    activo: bool = True


class CategoriaResponse(BaseModel):
    id: int
    nombre: str
    descripcion: str | None
    activo: bool
    orden: int


class ProductoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = None
    categoria_id: int | None = None
    precio_compra: int = Field(ge=0)
    precio_venta: int | None = Field(default=None, ge=0)
    stock_minimo: float = Field(default=0, ge=0)
    unidad_medida: str = "pz"


class ProductoUpdate(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str | None = None
    categoria_id: int | None = None
    precio_compra: int = Field(ge=0)
    precio_venta: int = Field(ge=0)
    stock_minimo: float = Field(ge=0)
    unidad_medida: str
    activo: bool = True


class ProductoResponse(BaseModel):
    id: int
    codigo: str
    nombre: str
    descripcion: str | None
    categoria_id: int | None
    precio_compra: int
    precio_venta: int
    stock_actual: float
    stock_minimo: float
    unidad_medida: str
    activo: bool
    stock_bajo: bool
    margen: float

    @classmethod
    def desde_entidad(cls, p) -> "ProductoResponse":
        return cls(
            id=p.id, codigo=p.codigo, nombre=p.nombre, descripcion=p.descripcion, categoria_id=p.categoria_id,
            precio_compra=p.precio_compra, precio_venta=p.precio_venta, stock_actual=float(p.stock_actual),
            stock_minimo=float(p.stock_minimo), unidad_medida=p.unidad_medida, activo=p.activo,
            stock_bajo=p.tiene_stock_bajo(), margen=p.margen(),
        )
