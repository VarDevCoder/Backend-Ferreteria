"""Libro de cuenta corriente de clientes (lo que cada uno debe).

El saldo no se guarda: es la suma de cargos menos pagos, así nunca queda
desfasado de los movimientos que lo explican.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.domain.entities import MovimientoCuentaCorriente
from app.domain.enums import MetodoPago, TipoMovimientoCuentaCorriente
from app.infrastructure.db.models import ClienteModel, MovimientoCuentaCorrienteModel

_M = MovimientoCuentaCorrienteModel
_SALDO = func.coalesce(func.sum(case((_M.tipo == TipoMovimientoCuentaCorriente.CARGO.value, _M.monto), else_=-_M.monto)), 0)


class SqlAlchemyCuentaCorrienteRepository:
    def __init__(self, session: Session):
        self._session = session

    def bloquear_cliente(self, cliente_id: int) -> None:
        """Toma la fila del cliente (FOR UPDATE): dos ventas a cuenta o cobros
        simultáneos del mismo cliente se validan de a uno contra su saldo."""
        self._session.execute(select(ClienteModel.id).where(ClienteModel.id == cliente_id).with_for_update())

    def saldo(self, cliente_id: int) -> int:
        return int(self._session.execute(select(_SALDO).where(_M.cliente_id == cliente_id)).scalar_one())

    def saldos(self) -> dict[int, int]:
        """Saldo de cada cliente que tuvo movimientos."""
        stmt = select(_M.cliente_id, _SALDO).group_by(_M.cliente_id)
        return {cliente_id: int(saldo) for cliente_id, saldo in self._session.execute(stmt)}

    def saldo_total(self) -> int:
        return int(self._session.execute(select(_SALDO)).scalar_one())

    def movimientos(self, cliente_id: int, limit: int | None = None) -> list[MovimientoCuentaCorriente]:
        stmt = select(_M).where(_M.cliente_id == cliente_id).order_by(_M.created_at.desc(), _M.id.desc())
        if limit:
            stmt = stmt.limit(limit)
        return [self._to_entity(r) for r in self._session.execute(stmt).scalars()]

    def add(self, movimiento: MovimientoCuentaCorriente) -> MovimientoCuentaCorriente:
        row = _M(
            cliente_id=movimiento.cliente_id, tipo=movimiento.tipo.value, monto=movimiento.monto,
            venta_id=movimiento.venta_id, metodo_pago=movimiento.metodo_pago.value if movimiento.metodo_pago else None,
            caja_turno_id=movimiento.caja_turno_id, referencia=movimiento.referencia, usuario_id=movimiento.usuario_id,
        )
        self._session.add(row)
        self._session.flush()
        self._session.refresh(row)
        return self._to_entity(row)

    def deudores(self, ahora: datetime | None = None) -> list[dict]:
        """Clientes con saldo a favor del negocio, con la antigüedad de la deuda.

        La antigüedad se calcula imputando los pagos a los cargos más viejos
        (FIFO), que es como lo entiende el cliente: "ya te pagué lo de marzo".
        """
        ahora = ahora or self._session.execute(select(func.now())).scalar_one().replace(tzinfo=None)
        con_saldo = (
            select(_M.cliente_id)
            .group_by(_M.cliente_id)
            .having(_SALDO > 0)
        )
        ids = list(self._session.execute(con_saldo).scalars())
        if not ids:
            return []
        clientes = {c.id: c for c in self._session.execute(select(ClienteModel).where(ClienteModel.id.in_(ids))).scalars()}
        movimientos = self._session.execute(
            select(_M).where(_M.cliente_id.in_(ids)).order_by(_M.created_at, _M.id)
        ).scalars()

        por_cliente: dict[int, dict] = {}
        for m in movimientos:
            d = por_cliente.setdefault(m.cliente_id, {"cargos": [], "pagado": 0, "ultimo_pago": None})
            if m.tipo == TipoMovimientoCuentaCorriente.CARGO.value:
                d["cargos"].append([m.created_at, m.monto])
            else:
                d["pagado"] += m.monto
                d["ultimo_pago"] = m.created_at

        resultado = []
        for cliente_id, d in por_cliente.items():
            restante = d["pagado"]
            pendientes = []
            for fecha, monto in d["cargos"]:
                imputado = min(restante, monto)
                restante -= imputado
                if monto - imputado > 0:
                    pendientes.append((fecha, monto - imputado))
            tramos = {"hasta_30": 0, "de_31_a_60": 0, "de_61_a_90": 0, "mas_de_90": 0}
            for fecha, pendiente in pendientes:
                dias = (ahora - fecha).days
                clave = "hasta_30" if dias <= 30 else "de_31_a_60" if dias <= 60 else "de_61_a_90" if dias <= 90 else "mas_de_90"
                tramos[clave] += pendiente
            cliente = clientes[cliente_id]
            saldo = sum(p for _, p in pendientes)
            resultado.append({
                "cliente_id": cliente_id,
                "nombre": cliente.nombre,
                "ruc": cliente.ruc,
                "telefono": cliente.telefono,
                "limite_credito": cliente.limite_credito,
                "saldo": saldo,
                "deuda_desde": pendientes[0][0] if pendientes else None,
                "dias_de_atraso": (ahora - pendientes[0][0]).days if pendientes else 0,
                "ultimo_pago": d["ultimo_pago"],
                **tramos,
            })
        resultado.sort(key=lambda r: r["saldo"], reverse=True)
        return resultado

    @staticmethod
    def _to_entity(row: MovimientoCuentaCorrienteModel) -> MovimientoCuentaCorriente:
        return MovimientoCuentaCorriente(
            id=row.id, cliente_id=row.cliente_id, tipo=TipoMovimientoCuentaCorriente(row.tipo), monto=row.monto,
            venta_id=row.venta_id, metodo_pago=MetodoPago(row.metodo_pago) if row.metodo_pago else None,
            caja_turno_id=row.caja_turno_id, referencia=row.referencia, usuario_id=row.usuario_id,
            created_at=row.created_at,
        )
