"""Cobro de pedidos de clientes: cómo se paga un pedido y cuándo entra la plata.

Formas de pago (`FormaPagoPedido`):
- ANTICIPADO: el cliente paga todo antes ("pagado a retirar" / "pagado a
  entregar"). No sale del depósito ni se entrega con saldo pendiente.
- CONTRA_ENTREGA: paga al recibir. Al entregar, el pedido queda con el cobro
  POR_RENDIR, sin mover la caja; después el repartidor rinde en la caja
  abierta con los medios del pago mixto (el efectivo entra al arqueo como
  ingreso). DECISIÓN A CONFIRMAR CON EL DUEÑO.
- CUENTA_CORRIENTE: al entregar, el saldo se carga a la cuenta corriente del
  cliente, con el límite de crédito de siempre.

En cualquier forma se pueden registrar señas o pagos anticipados. Todo cobro
de un pedido se registra con una caja abierta (queda asociado al turno); el
efectivo entra al arqueo como INGRESO. Los cobros con otros medios no suman a
los totales de ventas del turno (esos son de mostrador): en los reportes lo
cobrado por pedidos va en una línea aparte, "Ventas por pedidos".
"""
from __future__ import annotations

from app.application.services.cuenta_corriente_service import CuentaCorrienteService
from app.core.tiempo import ahora_utc
from app.domain.entities import MovimientoCaja, OrdenEnvio, PagoPedido, PedidoCliente
from app.domain.enums import (
    EstadoPagoPedido,
    EstadoPedidoCliente,
    FormaPagoPedido,
    MetodoPago,
    ModalidadEntrega,
    TipoMovimientoCaja,
    TipoPagoPedido,
)
from app.domain.exceptions import RecursoNoEncontrado, SolicitudInvalida, TransicionDeEstadoInvalida
from app.domain.repositories import CajaTurnoRepository, PagoPedidoRepository, PedidoClienteRepository


def _gs(monto: int) -> str:
    return f"Gs. {monto:,}".replace(",", ".")


def _enum(tipo, valor, nombre: str):
    if valor is None or valor == "":
        return None
    try:
        return tipo(valor)
    except ValueError:
        opciones = ", ".join(e.value for e in tipo)
        raise SolicitudInvalida(f"{nombre} no válido: {valor!r}. Opciones: {opciones}") from None


class CobroPedidoService:
    def __init__(
        self, pedidos: PedidoClienteRepository, pagos: PagoPedidoRepository, turnos: CajaTurnoRepository,
        cuenta_corriente: CuentaCorrienteService,
    ):
        self._pedidos = pedidos
        self._pagos = pagos
        self._turnos = turnos
        self._cuenta_corriente = cuenta_corriente

    # --- Consultas ------------------------------------------------------------------

    def listar_pagos(self, pedido_id: int) -> list[PagoPedido]:
        self._pedido(pedido_id)
        return self._pagos.list_by_pedido(pedido_id)

    def por_rendir(self) -> list[dict]:
        return self._pagos.por_rendir()

    # --- Condiciones del pedido -----------------------------------------------------

    @staticmethod
    def validar_condiciones_iniciales(modalidad: str | None, forma_pago: str | None, cliente_id: int | None) -> tuple:
        """Para el alta de un pedido: valores por defecto y reglas mínimas."""
        modalidad_ok = _enum(ModalidadEntrega, modalidad, "Modalidad de entrega") or ModalidadEntrega.ENTREGA_DOMICILIO
        forma_ok = _enum(FormaPagoPedido, forma_pago, "Forma de pago") or FormaPagoPedido.CONTRA_ENTREGA
        if forma_ok == FormaPagoPedido.CUENTA_CORRIENTE and not cliente_id:
            raise SolicitudInvalida("Para cobrar el pedido a cuenta elegí un cliente del catálogo (con crédito habilitado)")
        return modalidad_ok, forma_ok

    def cambiar_condiciones(
        self, pedido_id: int, modalidad_entrega: str | None = None, forma_pago: str | None = None,
    ) -> PedidoCliente:
        pedido = self._pedido(pedido_id, bloquear=True)
        modalidad = _enum(ModalidadEntrega, modalidad_entrega, "Modalidad de entrega")
        forma = _enum(FormaPagoPedido, forma_pago, "Forma de pago")
        if modalidad is not None and modalidad != pedido.modalidad_entrega:
            if not pedido.puede_cambiar_modalidad():
                raise TransicionDeEstadoInvalida(
                    "El pedido ya tiene un envío en curso: cancelá ese envío para cambiar cómo se entrega"
                )
            pedido.modalidad_entrega = modalidad
        if forma is not None and forma != pedido.forma_pago:
            if not pedido.puede_cambiar_forma_pago():
                raise TransicionDeEstadoInvalida("La forma de pago se cambia antes de entregar el pedido")
            if forma == FormaPagoPedido.CUENTA_CORRIENTE:
                if not pedido.cliente_id:
                    raise SolicitudInvalida("Para cobrar el pedido a cuenta elegí un cliente del catálogo")
                self._cuenta_corriente.validar_cargo(pedido.cliente_id, 0)  # crédito habilitado
            pedido.forma_pago = forma
        pedido.recalcular_estado_pago()
        return self._pedidos.update(pedido)

    # --- Señas y pagos anticipados --------------------------------------------------

    def registrar_anticipo(self, pedido_id: int, pagos: list[dict], usuario_id: int) -> PedidoCliente:
        """Seña o pago (total o parcial) antes de entregar."""
        turno = self._turno_abierto()
        pedido = self._pedido(pedido_id, bloquear=True)
        if pedido.estado == EstadoPedidoCliente.ENTREGADO:
            raise TransicionDeEstadoInvalida("El pedido ya se entregó: registrá el cobro como rendición")
        self._validar_puede_cobrar(pedido)
        for pago in self._validar_pagos(pagos, pedido.saldo(), permitir_cuenta=False):
            self._registrar(pedido, turno.id, TipoPagoPedido.ANTICIPO, pago, usuario_id, f"Seña / pago anticipado pedido {pedido.numero}")
        return self._actualizar_montos(pedido)

    def anular_pago(self, pedido_id: int, pago_id: int, motivo: str, usuario_id: int) -> PedidoCliente:
        """Devolución de una seña o pago anticipado (antes de entregar). Si fue
        en efectivo, sale de la caja abierta como RETIRO."""
        pago = self._pagos.get_by_id(pago_id)
        if pago is None or pago.pedido_cliente_id != pedido_id:
            raise RecursoNoEncontrado("Pago del pedido", pago_id)
        motivo = (motivo or "").strip()
        if not motivo:
            raise SolicitudInvalida("Indicá el motivo de la anulación")
        turno = self._turnos.get_abierto(bloquear=True) if pago.metodo == MetodoPago.EFECTIVO else None
        pedido = self._pedido(pedido_id, bloquear=True)
        pago = self._pagos.get_by_id(pago_id)  # releído con el pedido tomado
        if pago.anulado:
            raise TransicionDeEstadoInvalida("Ese pago ya fue anulado")
        if pago.tipo != TipoPagoPedido.ANTICIPO or pedido.estado == EstadoPedidoCliente.ENTREGADO:
            raise TransicionDeEstadoInvalida("Solo se anulan señas o pagos anticipados de un pedido sin entregar")
        if pago.metodo == MetodoPago.EFECTIVO:
            if turno is None:
                raise TransicionDeEstadoInvalida("Para devolver efectivo tiene que haber una caja abierta")
            self._turnos.agregar_movimiento(MovimientoCaja(
                id=None, caja_turno_id=turno.id, tipo=TipoMovimientoCaja.RETIRO, monto=pago.monto,
                motivo=f"Devolución de seña pedido {pedido.numero}: {motivo}", usuario_id=usuario_id,
            ))
        pago.anulado_at, pago.anulado_por, pago.motivo_anulacion = ahora_utc(), usuario_id, motivo
        self._pagos.anular(pago)
        return self._actualizar_montos(pedido)

    # --- Entrega y rendición --------------------------------------------------------

    def validar_salida(self, pedido: PedidoCliente) -> None:
        """Antes de despachar o entregar: un pedido con pago anticipado tiene
        que estar pagado, y uno a cuenta tiene que entrar en el crédito del cliente."""
        if pedido.forma_pago == FormaPagoPedido.ANTICIPADO and pedido.saldo() > 0:
            raise TransicionDeEstadoInvalida(
                f"El pedido {pedido.numero} es con pago anticipado y falta cobrar {_gs(pedido.saldo())}: "
                "registrá el pago o cambiá la forma de pago a contra entrega"
            )
        if pedido.forma_pago == FormaPagoPedido.CUENTA_CORRIENTE and pedido.saldo() > 0:
            self._cuenta_corriente.validar_cargo(pedido.cliente_id, pedido.saldo())

    def registrar_entrega(self, pedido: PedidoCliente, orden: OrdenEnvio, usuario_id: int) -> PedidoCliente:
        """El pedido se entregó (el llamador ya lo tomó con `bloquear` y validó
        con `validar_salida`). A cuenta: se carga el saldo. Contra entrega: queda
        POR_RENDIR. No mueve la caja."""
        pedido.estado = EstadoPedidoCliente.ENTREGADO
        if pedido.forma_pago == FormaPagoPedido.CUENTA_CORRIENTE and pedido.saldo() > 0:
            self._cargar_a_cuenta(pedido, pedido.saldo(), None, orden.id, usuario_id)
        return self._actualizar_montos(pedido)

    def rendir(self, pedido_id: int, pagos: list[dict], usuario_id: int) -> PedidoCliente:
        """El repartidor (o quien entregó) rinde en la caja lo cobrado contra
        entrega. Puede ser en partes. Lo que el cliente no pagó se puede cargar a
        su cuenta corriente (línea CUENTA_CORRIENTE)."""
        turno = self._turno_abierto()
        pedido = self._pedido(pedido_id, bloquear=True)
        if pedido.estado_pago != EstadoPagoPedido.POR_RENDIR:
            raise TransicionDeEstadoInvalida(f"El pedido {pedido.numero} no tiene cobros por rendir")
        for pago in self._validar_pagos(pagos, pedido.saldo(), permitir_cuenta=True):
            if pago["metodo"] == MetodoPago.CUENTA_CORRIENTE:
                if not pedido.cliente_id:
                    raise SolicitudInvalida("Para cargar a cuenta, el pedido tiene que ser de un cliente del catálogo")
                self._cuenta_corriente.validar_cargo(pedido.cliente_id, pago["monto"])
                self._cargar_a_cuenta(pedido, pago["monto"], turno.id, None, usuario_id, pago.get("referencia"))
            else:
                self._registrar(pedido, turno.id, TipoPagoPedido.RENDICION, pago, usuario_id, f"Rendición pedido {pedido.numero}")
        return self._actualizar_montos(pedido)

    # --- Auxiliares -----------------------------------------------------------------

    def _pedido(self, pedido_id: int, bloquear: bool = False) -> PedidoCliente:
        pedido = self._pedidos.bloquear(pedido_id) if bloquear else self._pedidos.get_by_id(pedido_id)
        if pedido is None:
            raise RecursoNoEncontrado("PedidoCliente", pedido_id)
        return pedido

    def _turno_abierto(self):
        turno = self._turnos.get_abierto(bloquear=True)
        if turno is None:
            raise TransicionDeEstadoInvalida("Los cobros de pedidos se registran en la caja: abrí la caja primero")
        return turno

    @staticmethod
    def _validar_puede_cobrar(pedido: PedidoCliente) -> None:
        if pedido.estado == EstadoPedidoCliente.CANCELADO:
            raise TransicionDeEstadoInvalida("El pedido está cancelado")
        if pedido.forma_pago is None:
            raise TransicionDeEstadoInvalida("Es un pedido anterior al registro de cobros: no se le cargan pagos")
        if pedido.saldo() <= 0:
            raise SolicitudInvalida(f"El pedido {pedido.numero} ya está pagado")

    @staticmethod
    def _validar_pagos(pagos: list[dict], saldo: int, permitir_cuenta: bool) -> list[dict]:
        if not pagos:
            raise SolicitudInvalida("Indicá al menos un pago")
        validos = set(MetodoPago.para_cobrar())
        if not permitir_cuenta:
            validos.discard(MetodoPago.CUENTA_CORRIENTE)
        resultado = []
        for p in pagos:
            metodo = _enum(MetodoPago, p.get("metodo"), "Medio de pago")
            if metodo not in validos:
                raise SolicitudInvalida(f"Medio de pago no válido aquí: {p.get('metodo')}")
            monto = int(p.get("monto") or 0)
            if monto <= 0:
                raise SolicitudInvalida("Cada pago tiene que ser mayor a cero")
            resultado.append({"metodo": metodo, "monto": monto, "referencia": (p.get("referencia") or "").strip() or None})
        if sum(1 for p in resultado if p["metodo"] == MetodoPago.CUENTA_CORRIENTE) > 1:
            raise SolicitudInvalida("Cargá el monto a cuenta en una sola línea")
        total = sum(p["monto"] for p in resultado)
        if total > saldo:
            raise SolicitudInvalida(f"Los pagos ({_gs(total)}) superan lo que falta cobrar ({_gs(saldo)})")
        return resultado

    def _registrar(self, pedido: PedidoCliente, turno_id: int, tipo: TipoPagoPedido, pago: dict, usuario_id: int, motivo: str) -> None:
        if pago["metodo"] == MetodoPago.EFECTIVO:
            self._turnos.agregar_movimiento(MovimientoCaja(
                id=None, caja_turno_id=turno_id, tipo=TipoMovimientoCaja.INGRESO, monto=pago["monto"],
                motivo=f"{motivo} ({pedido.cliente_nombre})", usuario_id=usuario_id,
            ))
        self._pagos.add(PagoPedido(
            id=None, pedido_cliente_id=pedido.id, tipo=tipo, metodo=pago["metodo"], monto=pago["monto"],
            referencia=pago.get("referencia"), caja_turno_id=turno_id, usuario_id=usuario_id,
        ))

    def _cargar_a_cuenta(
        self, pedido: PedidoCliente, monto: int, turno_id: int | None, orden_envio_id: int | None, usuario_id: int,
        referencia: str | None = None,
    ) -> None:
        self._cuenta_corriente.registrar_cargo(
            pedido.cliente_id, monto, venta_id=None, caja_turno_id=turno_id,
            referencia=f"Pedido {pedido.numero}", usuario_id=usuario_id, pedido_cliente_id=pedido.id,
        )
        self._pagos.add(PagoPedido(
            id=None, pedido_cliente_id=pedido.id, tipo=TipoPagoPedido.CARGO_CUENTA, metodo=MetodoPago.CUENTA_CORRIENTE,
            monto=monto, referencia=referencia, caja_turno_id=turno_id, orden_envio_id=orden_envio_id, usuario_id=usuario_id,
        ))

    def _actualizar_montos(self, pedido: PedidoCliente) -> PedidoCliente:
        vigentes = self._pagos.list_by_pedido(pedido.id, incluir_anulados=False)
        pedido.monto_a_cuenta = sum(p.monto for p in vigentes if p.metodo == MetodoPago.CUENTA_CORRIENTE)
        pedido.monto_pagado = sum(p.monto for p in vigentes if p.metodo != MetodoPago.CUENTA_CORRIENTE)
        pedido.recalcular_estado_pago()
        return self._pedidos.update(pedido)
