"""Cuenta corriente de clientes ("cuenta a cubrir"): lo que se vende fiado y se cobra después.

- Cada cliente tiene un límite de crédito (0 = no compra a cuenta). Lo fija
  un administrador o encargado, no el vendedor.
- Una venta con parte (o todo) "a cuenta" genera un CARGO; cada cobro, un PAGO.
- Un cobro en efectivo entra a la caja abierta como ingreso, así el arqueo
  del turno lo incluye.
"""
from app.domain.entities import Cliente, MovimientoCaja, MovimientoCuentaCorriente
from app.domain.enums import MetodoPago, TipoMovimientoCaja, TipoMovimientoCuentaCorriente
from app.domain.exceptions import RecursoNoEncontrado, SolicitudInvalida, TransicionDeEstadoInvalida
from app.domain.repositories import CajaTurnoRepository, ClienteRepository, CuentaCorrienteRepository


class CuentaCorrienteService:
    def __init__(self, cuentas: CuentaCorrienteRepository, clientes: ClienteRepository, turnos: CajaTurnoRepository):
        self._cuentas = cuentas
        self._clientes = clientes
        self._turnos = turnos

    def _cliente(self, cliente_id: int) -> Cliente:
        cliente = self._clientes.get_by_id(cliente_id)
        if cliente is None:
            raise RecursoNoEncontrado("Cliente", cliente_id)
        return cliente

    def estado_de_cuenta(self, cliente_id: int, limit: int = 100) -> dict:
        cliente = self._cliente(cliente_id)
        saldo = self._cuentas.saldo(cliente_id)
        return {
            "cliente_id": cliente.id,
            "nombre": cliente.nombre,
            "limite_credito": cliente.limite_credito,
            "saldo": saldo,
            "disponible": max(0, cliente.limite_credito - saldo),
            "movimientos": self._cuentas.movimientos(cliente_id, limit=limit),
        }

    def saldos(self) -> dict[int, int]:
        return self._cuentas.saldos()

    def deudores(self) -> list[dict]:
        return self._cuentas.deudores()

    def total_por_cobrar(self) -> int:
        return self._cuentas.saldo_total()

    def validar_cargo(self, cliente_id: int | None, monto: int) -> None:
        """Verifica que el cliente pueda llevarse `monto` a cuenta."""
        if not cliente_id:
            raise SolicitudInvalida("Para vender a cuenta tenés que elegir el cliente")
        self._cuentas.bloquear_cliente(cliente_id)  # dos ventas a cuenta simultáneas: de a una
        cliente = self._cliente(cliente_id)
        if not cliente.activo:
            raise SolicitudInvalida(f"{cliente.nombre} está inactivo")
        if cliente.limite_credito <= 0:
            raise SolicitudInvalida(
                f"{cliente.nombre} no tiene crédito habilitado. Un encargado puede asignarle un límite en Clientes"
            )
        disponible = cliente.limite_credito - self._cuentas.saldo(cliente_id)
        if monto > disponible:
            raise SolicitudInvalida(
                f"{cliente.nombre} supera su límite de crédito: le quedan Gs. {max(0, disponible):,} disponibles".replace(",", ".")
            )

    def registrar_cargo(self, cliente_id: int, monto: int, venta_id: int, caja_turno_id: int, referencia: str, usuario_id: int) -> None:
        self._cuentas.add(
            MovimientoCuentaCorriente(
                id=None, cliente_id=cliente_id, tipo=TipoMovimientoCuentaCorriente.CARGO, monto=monto,
                venta_id=venta_id, caja_turno_id=caja_turno_id, referencia=referencia, usuario_id=usuario_id,
            )
        )

    def registrar_cobro(
        self, cliente_id: int, monto: int, metodo: str, referencia: str | None, usuario_id: int
    ) -> MovimientoCuentaCorriente:
        # Mismo orden de bloqueo que una venta (turno y después cliente).
        turno = self._turnos.get_abierto(bloquear=True)
        self._cuentas.bloquear_cliente(cliente_id)
        cliente = self._cliente(cliente_id)
        try:
            metodo_pago = MetodoPago(metodo)
        except ValueError:
            raise SolicitudInvalida(f"Medio de pago desconocido: {metodo}") from None
        if metodo_pago not in MetodoPago.para_cobrar() or metodo_pago == MetodoPago.CUENTA_CORRIENTE:
            raise SolicitudInvalida("Elegí con qué paga el cliente (efectivo, tarjeta, transferencia...)")
        if monto <= 0:
            raise SolicitudInvalida("El monto debe ser mayor a cero")
        saldo = self._cuentas.saldo(cliente_id)
        if monto > saldo:
            raise SolicitudInvalida(
                f"{cliente.nombre} debe Gs. {saldo:,}; no se puede cobrar más que eso".replace(",", ".")
            )

        if metodo_pago == MetodoPago.EFECTIVO:
            if turno is None:
                raise TransicionDeEstadoInvalida("Para cobrar en efectivo tiene que haber una caja abierta")
            self._turnos.agregar_movimiento(
                MovimientoCaja(
                    id=None, caja_turno_id=turno.id, tipo=TipoMovimientoCaja.INGRESO, monto=monto,
                    motivo=f"Cobro de cuenta corriente: {cliente.nombre}", usuario_id=usuario_id,
                )
            )
        return self._cuentas.add(
            MovimientoCuentaCorriente(
                id=None, cliente_id=cliente_id, tipo=TipoMovimientoCuentaCorriente.PAGO, monto=monto,
                metodo_pago=metodo_pago, caja_turno_id=turno.id if turno else None,
                referencia=referencia or "Cobro", usuario_id=usuario_id,
            )
        )
