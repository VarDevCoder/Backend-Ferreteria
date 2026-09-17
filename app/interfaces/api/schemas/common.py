from pydantic import BaseModel


class Mensaje(BaseModel):
    mensaje: str


class MotivoRequerido(BaseModel):
    motivo: str


class ObservacionesRequeridas(BaseModel):
    observaciones: str
