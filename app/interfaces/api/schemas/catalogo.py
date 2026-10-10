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
    # Código interno o de barras. Vacío = se genera automáticamente.
    codigo: str | None = Field(default=None, max_length=50)
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
    stock_actual: float          # stock vendible (el que usan la caja, los pedidos y los envíos)
    stock_minimo: float
    unidad_medida: str
    activo: bool
    stock_bajo: bool
    margen: float
    # Si admite cantidades con decimales (m, kg, lt); si no, solo enteras.
    fraccionable: bool = False
    stock_no_vendible: float = 0  # averiado, vencido, etc. (existe pero no se vende)
    stock_total: float = 0        # vendible + no vendible

    @classmethod
    def desde_entidad(cls, p) -> "ProductoResponse":
        return cls(
            id=p.id, codigo=p.codigo, nombre=p.nombre, descripcion=p.descripcion, categoria_id=p.categoria_id,
            precio_compra=p.precio_compra, precio_venta=p.precio_venta, stock_actual=float(p.stock_actual),
            stock_minimo=float(p.stock_minimo), unidad_medida=p.unidad_medida, activo=p.activo,
            stock_bajo=p.tiene_stock_bajo(), margen=p.margen(), fraccionable=p.es_fraccionable(),
            stock_no_vendible=float(p.stock_no_vendible or 0), stock_total=float(p.stock_total()),
        )
