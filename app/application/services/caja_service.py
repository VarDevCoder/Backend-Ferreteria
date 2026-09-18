"""Casos de uso de Caja y venta de mostrador.

Cubre el flujo que ANKOR no tenía: alguien entra al local, compra al contado
y se va. Eso exige un turno de caja abierto (RF: no se puede vender sin caja
abierta), descuenta stock igual que una orden de envío, y el turno se cierra
con arqueo (conteo físico vs. lo que el sistema esperaba encontrar).
"""
from datetime import datetime
from decimal import Decimal

from app.domain.entities import CajaTurno, MovimientoCaja, MovimientoInventario, VentaMostrador, VentaMostradorItem
from app.domain.enums import MetodoPago, TipoMovimientoCaja, TipoMovimientoInventario, TipoReferenciaMovimiento
from app.domain.exceptions import RecursoNoEncontrado, SolicitudInvalida, StockInsuficiente, TransicionDeEstadoInvalida
from app.domain.repositories import (
    CajaTurnoRepository,
    MovimientoInventarioRepository,
    ProductoRepository,
    VentaMostradorRepository,
)


class CajaService:
    def __init__(
        self,
        turnos: CajaTurnoRepository,
        ventas: VentaMostradorRepository,
        productos: ProductoRepository,
        movimientos: MovimientoInventarioRepository,
    ):
        self._turnos = turnos
        self._ventas = ventas
        self._productos = productos
        self._movimientos = movimientos

    # --- Turnos ------------------------------------------------------------

    def turno_abierto(self) -> CajaTurno | None:
        return self._turnos.get_abierto()

    def historial_turnos(self, limit: int = 30) -> list[CajaTurno]:
        return self._turnos.list(limit=limit)

    def obtener_turno(self, turno_id: int) -> CajaTurno:
        turno = self._turnos.get_by_id(turno_id)
        if turno is None:
            raise RecursoNoEncontrado("CajaTurno", turno_id)
        return turno

    def abrir_turno(self, usuario_id: int, fondo_inicial: int) -> CajaTurno:
        if self._turnos.get_abierto() is not None:
            raise TransicionDeEstadoInvalida("Ya hay un turno de caja abierto")
        if fondo_inicial < 0:
            raise SolicitudInvalida("El fondo inicial no puede ser negativo")
        turno = CajaTurno(id=None, usuario_id=usuario_id, fondo_inicial=fondo_inicial)
        return self._turnos.add(turno)

    def registrar_movimiento(self, turno_id: int, tipo: str, monto: int, motivo: str | None, usuario_id: int) -> CajaTurno:
        turno = self.obtener_turno(turno_id)
        if not turno.puede_registrar_ventas():
            raise TransicionDeEstadoInvalida("El turno de caja no está abierto")
        if monto <= 0:
            raise SolicitudInvalida("El monto debe ser mayor a cero")
        self._turnos.agregar_movimiento(
            MovimientoCaja(
                id=None, caja_turno_id=turno_id, tipo=TipoMovimientoCaja(tipo), monto=monto,
                motivo=motivo, usuario_id=usuario_id,
            )
        )
        return self.obtener_turno(turno_id)

    def cerrar_turno(self, turno_id: int, conteo_fisico: int, notas: str | None) -> CajaTurno:
        turno = self.obtener_turno(turno_id)
        if not turno.puede_cerrarse():
            raise TransicionDeEstadoInvalida("El turno ya está cerrado")
        if conteo_fisico < 0:
            raise SolicitudInvalida("El conteo físico no puede ser negativo")

        turno.calcular_cierre(conteo_fisico)
        turno.notas = notas
        turno.fecha_cierre = datetime.now()
        return self._turnos.update(turno)

    # --- Ventas de mostrador -------------------------------------------------

    def listar_ventas(self, caja_turno_id: int | None = None, limit: int = 100) -> list[VentaMostrador]:
        return self._ventas.list(caja_turno_id=caja_turno_id, limit=limit)

    def registrar_venta(
        self,
        usuario_id: int,
        items: list[dict],
        metodo_pago: str = MetodoPago.EFECTIVO,
        cliente_id: int | None = None,
        descuento: int = 0,
        notas: str | None = None,
    ) -> VentaMostrador:
        turno = self._turnos.get_abierto()
        if turno is None:
            raise TransicionDeEstadoInvalida("No hay un turno de caja abierto. Abrí caja antes de vender.")
        if not items:
            raise SolicitudInvalida("La venta debe tener al menos un ítem")

        venta_items = []
        for i in items:
            producto = self._productos.get_by_id(i["producto_id"])
            if producto is None:
                raise RecursoNoEncontrado("Producto", i["producto_id"])
            cantidad = Decimal(str(i["cantidad"]))
            if cantidad <= 0:
                raise SolicitudInvalida(f"La cantidad de {producto.nombre} debe ser mayor a cero")
            if producto.stock_actual < cantidad:
                raise StockInsuficiente(producto.nombre, producto.stock_actual, cantidad)
            venta_items.append(
                VentaMostradorItem(
                    id=None, venta_id=None, producto_id=producto.id, cantidad=cantidad,
                    precio_unitario=i.get("precio_unitario") or producto.precio_venta,
                )
            )

        venta = VentaMostrador(
            id=None,
            numero=self._ventas.siguiente_numero(),
            caja_turno_id=turno.id,
            usuario_id=usuario_id,
            cliente_id=cliente_id,
            metodo_pago=MetodoPago(metodo_pago),
            descuento=descuento,
            notas=notas,
            items=venta_items,
        )
        venta.calcular_totales()
        venta = self._ventas.add(venta)

        for item in venta.items:
            producto = self._productos.get_by_id(item.producto_id)
            stock_anterior = producto.stock_actual
            stock_nuevo = stock_anterior - item.cantidad
            producto.stock_actual = stock_nuevo
            self._productos.update(producto)
            self._movimientos.add(
                MovimientoInventario(
                    id=None, producto_id=producto.id, tipo=TipoMovimientoInventario.SALIDA,
                    cantidad=item.cantidad, stock_anterior=stock_anterior, stock_nuevo=stock_nuevo,
                    referencia_tipo=TipoReferenciaMovimiento.VENTA_MOSTRADOR, referencia_id=venta.id,
                    usuario_id=usuario_id, observaciones=f"Venta de mostrador {venta.numero}",
                )
            )

        self._turnos.acumular_venta(turno.id, venta.metodo_pago.value, venta.total)
        return venta

    def resumen_hoy(self) -> dict:
        return {
            "ventas_hoy": self._ventas.contar_hoy(),
            "total_hoy": self._ventas.total_hoy(),
        }
