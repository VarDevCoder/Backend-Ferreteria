from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Usuario
from app.domain.enums import RolUsuario
from app.infrastructure.db.models import UsuarioModel


class SqlAlchemyUsuarioRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, usuario_id: int) -> Usuario | None:
        row = self._session.get(UsuarioModel, usuario_id)
        return self._to_entity(row) if row else None

    def get_by_email(self, email: str) -> Usuario | None:
        row = self._session.execute(
            select(UsuarioModel).where(UsuarioModel.email == email)
        ).scalar_one_or_none()
        return self._to_entity(row) if row else None

    def add(self, usuario: Usuario) -> Usuario:
        row = self._to_model(usuario)
        self._session.add(row)
        self._session.flush()
        return self._to_entity(row)

    def update(self, usuario: Usuario) -> Usuario:
        row = self._session.get(UsuarioModel, usuario.id)
        if row is None:
            raise ValueError(f"Usuario {usuario.id} no existe")
        row.name = usuario.name
        row.email = usuario.email
        row.password_hash = usuario.password_hash
        row.rol = usuario.rol.value
        row.activo = usuario.activo
        self._session.flush()
        return self._to_entity(row)

    def list_by_rol(self, rol: str) -> list[Usuario]:
        rows = self._session.execute(select(UsuarioModel).where(UsuarioModel.rol == rol)).scalars().all()
        return [self._to_entity(r) for r in rows]

    @staticmethod
    def _to_entity(row: UsuarioModel) -> Usuario:
        return Usuario(
            id=row.id,
            name=row.name,
            email=row.email,
            password_hash=row.password_hash,
            rol=RolUsuario(row.rol),
            activo=row.activo,
            created_at=row.created_at,
        )

    @staticmethod
    def _to_model(usuario: Usuario) -> UsuarioModel:
        return UsuarioModel(
            id=usuario.id,
            name=usuario.name,
            email=usuario.email,
            password_hash=usuario.password_hash,
            rol=usuario.rol.value,
            activo=usuario.activo,
        )
