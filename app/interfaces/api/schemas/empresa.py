from pydantic import BaseModel, Field


class EmpresaBase(BaseModel):
    nombre_comercial: str = Field(min_length=1, max_length=255)
    razon_social: str | None = Field(default=None, max_length=255)
    ruc: str | None = Field(default=None, max_length=50)
    direccion: str | None = None
    ciudad: str | None = Field(default=None, max_length=100)
    telefono: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    moneda_codigo: str = Field(default="PYG", min_length=3, max_length=3, description="Código ISO 4217, ej. PYG, ARS, CLP")
    moneda_simbolo: str = Field(default="Gs.", min_length=1, max_length=10)
    locale: str = Field(default="es-PY", max_length=20, description="Formato regional de números y fechas, ej. es-PY, es-AR")
    iva_porcentaje: int = Field(default=10, ge=0, le=100)
    margen_ganancia_defecto: int = Field(default=25, ge=0, le=1000)
    pie_ticket: str | None = None


class EmpresaResponse(EmpresaBase):
    pass


class EmpresaUpdate(EmpresaBase):
    pass


class EstadoConfiguracionResponse(BaseModel):
    requiere_configuracion: bool


class AdminInicial(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=255)


class ConfiguracionInicialInput(BaseModel):
    empresa: EmpresaUpdate
    admin: AdminInicial

