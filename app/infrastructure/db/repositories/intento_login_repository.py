from datetime import timedelta

from sqlalchemy import delete, func, select

from app.core.tiempo import ahora_utc
from app.infrastructure.db.models import IntentoLoginFallidoModel
from app.infrastructure.db.session import SessionLocal


class SqlAlchemyIntentoLoginRepository:
    """Usa su propia sesión y comitea al instante: el intento fallido tiene
    que quedar guardado aunque el request termine en error (y la sesión del
    request haga rollback)."""

    def contar_recientes(self, email: str, ventana_segundos: int) -> int:
        desde = ahora_utc() - timedelta(seconds=ventana_segundos)
        with SessionLocal() as db:
            return db.execute(
                select(func.count()).select_from(IntentoLoginFallidoModel).where(
                    IntentoLoginFallidoModel.email == email, IntentoLoginFallidoModel.created_at >= desde
                )
            ).scalar_one()

    def registrar_fallo(self, email: str) -> None:
        with SessionLocal() as db:
            db.add(IntentoLoginFallidoModel(email=email, created_at=ahora_utc()))
            db.commit()

    def limpiar(self, email: str, mas_viejos_que_segundos: int) -> None:
        """Borra los intentos de este email y, de paso, los vencidos de todos."""
        limite = ahora_utc() - timedelta(seconds=mas_viejos_que_segundos)
        with SessionLocal() as db:
            db.execute(delete(IntentoLoginFallidoModel).where(
                (IntentoLoginFallidoModel.email == email) | (IntentoLoginFallidoModel.created_at < limite)
            ))
            db.commit()
