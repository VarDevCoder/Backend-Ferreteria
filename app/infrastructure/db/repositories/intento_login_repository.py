from datetime import timedelta

from sqlalchemy import delete, func, select

from app.core.tiempo import ahora_utc
from app.infrastructure.db.models import IntentoLoginFallidoModel
from app.infrastructure.db.session import SessionLocal


class SqlAlchemyIntentoLoginRepository:
    """Usa su propia sesión y comitea al instante: el intento fallido tiene
    que quedar guardado aunque el request termine en error (y la sesión del
    request haga rollback)."""

    def contar_recientes(self, ventana_segundos: int, email: str | None = None, ip: str | None = None) -> int:
        """Fallos dentro de la ventana para ese email, esa IP o ambos."""
        desde = ahora_utc() - timedelta(seconds=ventana_segundos)
        stmt = select(func.count()).select_from(IntentoLoginFallidoModel).where(IntentoLoginFallidoModel.created_at >= desde)
        if email is not None:
            stmt = stmt.where(IntentoLoginFallidoModel.email == email)
        if ip is not None:
            stmt = stmt.where(IntentoLoginFallidoModel.ip == ip)
        with SessionLocal() as db:
            return db.execute(stmt).scalar_one()

    def registrar_fallo(self, email: str, ip: str | None) -> None:
        with SessionLocal() as db:
            db.add(IntentoLoginFallidoModel(email=email, ip=ip, created_at=ahora_utc()))
            db.commit()

    def limpiar(self, email: str, ip: str | None, mas_viejos_que_segundos: int) -> None:
        """Borra los fallos de este email desde esta IP (los de otras conexiones
        siguen contando) y, de paso, los vencidos de todos."""
        limite = ahora_utc() - timedelta(seconds=mas_viejos_que_segundos)
        de_esta_conexion = (IntentoLoginFallidoModel.email == email) & (
            IntentoLoginFallidoModel.ip.is_(None) if ip is None else IntentoLoginFallidoModel.ip == ip
        )
        with SessionLocal() as db:
            db.execute(delete(IntentoLoginFallidoModel).where(de_esta_conexion | (IntentoLoginFallidoModel.created_at < limite)))
            db.commit()
