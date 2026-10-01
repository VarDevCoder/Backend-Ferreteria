from dataclasses import asdict, fields

from sqlalchemy.orm import Session

from app.domain.entities import Empresa
from app.infrastructure.db.models import EmpresaModel

_EMPRESA_ID = 1
_CAMPOS = [f.name for f in fields(Empresa)]


class SqlAlchemyEmpresaRepository:
    """La configuración de la empresa es una sola fila (id=1). Si todavía no
    existe, `get` devuelve los valores por defecto sin escribir nada."""

    def __init__(self, session: Session):
        self._session = session

    def get(self) -> Empresa:
        row = self._session.get(EmpresaModel, _EMPRESA_ID)
        if row is None:
            return Empresa()
        return Empresa(**{campo: getattr(row, campo) for campo in _CAMPOS})

    def save(self, empresa: Empresa) -> Empresa:
        row = self._session.get(EmpresaModel, _EMPRESA_ID)
        if row is None:
            row = EmpresaModel(id=_EMPRESA_ID)
            self._session.add(row)
        for campo, valor in asdict(empresa).items():
            setattr(row, campo, valor)
        self._session.flush()
        return self.get()
