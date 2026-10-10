"""Cobros de pedidos: señas, pagos anticipados, rendiciones del cobro contra
entrega y cargos a cuenta corriente al entregar."""
from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.domain.entities import PagoPedido
from app.domain.enums import EstadoOrdenEnvio, EstadoPagoPedido, MetodoPago, TipoPagoPedido
from app.infrastructure.db.models import OrdenEnvioModel, PedidoClienteModel, PedidoPagoModel, UsuarioModel


class SqlAlchemyPagoPedidoRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, pago: PagoPedido) -> PagoPedido:
        row = PedidoPagoModel(
            pedido_cliente_id=pago.pedido_cliente_id, tipo=pago.tipo.value, metodo=pago.metodo.value, monto=pago.monto,
            referencia=pago.referencia, caja_turno_id=pago.caja_turno_id, orden_envio_id=pago.orden_envio_id,
            usuario_id=pago.usuario_id,
        )
        self._session.add(row)
        self._session.flush()
        return self.get_by_id(row.id)

    def get_by_id(self, pago_id: int) -> PagoPedido | None:
        pagos = self._consultar(PedidoPagoModel.id == pago_id)
        return pagos[0] if pagos else None

    def list_by_pedido(self, pedido_id: int, incluir_anulados: bool = True) -> list[PagoPedido]:
        condiciones = [PedidoPagoModel.pedido_cliente_id == pedido_id]
        if not incluir_anulados:
            condiciones.append(PedidoPagoModel.anulado.is_(False))
        return self._consultar(*condiciones)

    def anular(self, pago: PagoPedido) -> PagoPedido:
        row = self._session.get(PedidoPagoModel, pago.id)
        row.anulado = True
        row.anulado_at = pago.anulado_at
        row.anulado_por = pago.anulado_por
        row.motivo_anulacion = pago.motivo_anulacion
        self._session.flush()
        return self.get_by_id(pago.id)

    def por_rendir(self) -> list[dict]:
        """Pedidos entregados contra entrega con saldo sin rendir, con el envío
        que los entregó (quién lo llevó y cuándo). Una sola consulta."""
        entrega = (
            select(
                OrdenEnvioModel.pedido_cliente_id.label("pedido_id"),
                func.max(OrdenEnvioModel.id).label("orden_id"),
            )
            .where(OrdenEnvioModel.estado == EstadoOrdenEnvio.ENTREGADO.value)
            .group_by(OrdenEnvioModel.pedido_cliente_id)
            .subquery()
        )
        stmt = (
            select(PedidoClienteModel, OrdenEnvioModel)
            .outerjoin(entrega, entrega.c.pedido_id == PedidoClienteModel.id)
            .outerjoin(OrdenEnvioModel, and_(OrdenEnvioModel.id == entrega.c.orden_id))
            .where(PedidoClienteModel.estado_pago == EstadoPagoPedido.POR_RENDIR.value)
            .order_by(OrdenEnvioModel.fecha_entrega.asc().nulls_last(), PedidoClienteModel.id)
        )
        filas = []
        for pedido, orden in self._session.execute(stmt).all():
            saldo = max(0, pedido.total - (pedido.monto_pagado or 0) - (pedido.monto_a_cuenta or 0))
            filas.append({
                "pedido_id": pedido.id,
                "numero": pedido.numero,
                "cliente_id": pedido.cliente_id,
                "cliente_nombre": pedido.cliente_nombre,
                "cliente_telefono": pedido.cliente_telefono,
                "modalidad_entrega": pedido.modalidad_entrega,
                "total": pedido.total,
                "monto_pagado": pedido.monto_pagado or 0,
                "por_rendir": saldo,
                "orden_envio_id": orden.id if orden else None,
                "orden_envio_numero": orden.numero if orden else None,
                "fecha_entrega": orden.fecha_entrega if orden else None,
                "transportista": orden.transportista if orden else None,
                "conductor_nombre": orden.conductor_nombre if orden else None,
            })
        return filas

    def _consultar(self, *condiciones) -> list[PagoPedido]:
        stmt = (
            select(PedidoPagoModel, UsuarioModel.name)
            .outerjoin(UsuarioModel, UsuarioModel.id == PedidoPagoModel.usuario_id)
            .where(*condiciones)
            .order_by(PedidoPagoModel.created_at, PedidoPagoModel.id)
        )
        return [
            PagoPedido(
                id=r.id, pedido_cliente_id=r.pedido_cliente_id, tipo=TipoPagoPedido(r.tipo), metodo=MetodoPago(r.metodo),
                monto=r.monto, referencia=r.referencia, caja_turno_id=r.caja_turno_id, orden_envio_id=r.orden_envio_id,
                usuario_id=r.usuario_id, usuario_nombre=nombre, created_at=r.created_at, anulado=r.anulado,
                anulado_at=r.anulado_at, anulado_por=r.anulado_por, motivo_anulacion=r.motivo_anulacion,
            )
            for r, nombre in self._session.execute(stmt).all()
        ]
