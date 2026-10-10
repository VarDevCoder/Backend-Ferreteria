"""Casos de uso de stock no vendible y reclamos al proveedor.

Stock no vendible: unidades averiadas, abolladas, vencidas o con defecto de
fábrica. Se separan del stock vendible (`Producto.stock_actual`, el único
que usan la caja, los pedidos y los envíos) y pasan a
`Producto.stock_no_vendible`: siguen existiendo hasta que se resuelven.

Formas de resolverlas:
- reparadas: vuelven a stock vendible (TRASPASO en el kardex);
- descartadas: baja con pérdida (BAJA en el kardex);
- reclamadas al proveedor: el reclamo, una vez aceptado, resuelve cada ítem
  con reposición (sale lo no vendible y entra mercadería nueva), nota de
  crédito (sale lo no vendible) o rechazo (las unidades siguen no vendibles).

Todo movimiento queda en el kardex con el stock vendible y el no vendible
antes y después, quién lo hizo y cuándo.
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from app.domain.entities import (
    Empresa,
    MovimientoInventario,
    Producto,
    ReclamoProveedor,
    ReclamoProveedorItem,
    ResolucionNoVendible,
    StockNoVendible,
)
from app.domain.enums import (
    EstadoReclamoProveedor,
    EstadoStockNoVendible,
    MotivoNoVendible,
    ResolucionItemReclamo,
    TipoMovimientoInventario,
    TipoReferenciaMovimiento,
    TipoResolucionNoVendible,
)
from app.domain.exceptions import (
    RecursoNoEncontrado,
    SolicitudInvalida,
    StockInsuficiente,
    TransicionDeEstadoInvalida,
)
from app.domain.repositories import (
    EmpresaRepository,
    MovimientoInventarioRepository,
    ProveedorRepository,
    ReclamoProveedorRepository,
    StockNoVendibleRepository,
)

ETIQUETA_MOTIVO = {
    MotivoNoVendible.AVERIADO: "averiado",
    MotivoNoVendible.ABOLLADO: "abollado",
    MotivoNoVendible.VENCIDO: "vencido",
    MotivoNoVendible.DEFECTO_FABRICA: "defecto de fábrica",
    MotivoNoVendible.OTRO: "otro motivo",
}
_MIL = Decimal("0.001")


def _cantidad(valor, campo: str = "La cantidad") -> Decimal:
    cantidad = Decimal(str(valor)).quantize(_MIL, rounding=ROUND_HALF_UP)
    if cantidad <= 0:
        raise SolicitudInvalida(f"{campo} tiene que ser mayor que cero")
    return cantidad


def _texto(valor: str | None) -> str | None:
    valor = (valor or "").strip()
    return valor or None


def _enum(tipo, valor: str | None, nombre: str):
    if valor is None or valor == "":
        return None
    try:
        return tipo(valor)
    except ValueError:
        opciones = ", ".join(e.value for e in tipo)
        raise SolicitudInvalida(f"{nombre} no válido: {valor!r}. Opciones: {opciones}") from None


def _fmt(cantidad: Decimal) -> str:
    return f"{cantidad.normalize():f}"


class _Stock:
    """Mueve stock vendible y no vendible de un producto (con la fila
    bloqueada) y deja el movimiento en el kardex."""

    def __init__(self, registros: StockNoVendibleRepository, movimientos: MovimientoInventarioRepository):
        self._registros = registros
        self._movimientos = movimientos

    def mover(
        self, producto_id: int, *, delta_vendible: Decimal, delta_no_vendible: Decimal,
        tipo: TipoMovimientoInventario, cantidad: Decimal, referencia_tipo: TipoReferenciaMovimiento,
        referencia_id: int, usuario_id: int | None, observaciones: str,
    ) -> Producto:
        producto = self._registros.bloquear_producto(producto_id)
        if producto is None:
            raise RecursoNoEncontrado("Producto", producto_id)
        vendible_antes, no_vendible_antes = producto.stock_actual, producto.stock_no_vendible
        vendible, no_vendible = vendible_antes + delta_vendible, no_vendible_antes + delta_no_vendible
        if vendible < 0:
            raise StockInsuficiente(producto.nombre, _fmt(vendible_antes), _fmt(-delta_vendible))
        if no_vendible < 0:
            raise StockInsuficiente(f"{producto.nombre} (no vendible)", _fmt(no_vendible_antes), _fmt(-delta_no_vendible))
        self._registros.guardar_stock(producto_id, vendible, no_vendible)
        self._movimientos.add(MovimientoInventario(
            id=None, producto_id=producto_id, tipo=tipo, cantidad=cantidad,
            stock_anterior=vendible_antes, stock_nuevo=vendible,
            referencia_tipo=referencia_tipo, referencia_id=referencia_id, usuario_id=usuario_id,
            observaciones=observaciones, no_vendible_anterior=no_vendible_antes, no_vendible_nuevo=no_vendible,
        ))
        producto.stock_actual, producto.stock_no_vendible = vendible, no_vendible
        return producto


class StockNoVendibleService:
    def __init__(
        self, registros: StockNoVendibleRepository, movimientos: MovimientoInventarioRepository,
        proveedores: ProveedorRepository,
    ):
        self._registros = registros
        self._proveedores = proveedores
        self._stock = _Stock(registros, movimientos)

    def listar(
        self, estado: str | None = None, producto_id: int | None = None,
        proveedor_id: int | None = None, motivo: str | None = None,
    ) -> list[StockNoVendible]:
        estado_ok = _enum(EstadoStockNoVendible, estado, "Estado")
        motivo_ok = _enum(MotivoNoVendible, motivo, "Motivo")
        return self._registros.list(
            estado=estado_ok.value if estado_ok else None, producto_id=producto_id,
            proveedor_id=proveedor_id, motivo=motivo_ok.value if motivo_ok else None,
        )

    def obtener(self, registro_id: int) -> StockNoVendible:
        registro = self._registros.get_by_id(registro_id)
        if registro is None:
            raise RecursoNoEncontrado("Registro de stock no vendible", registro_id)
        return registro

    def marcar(
        self, producto_id: int, cantidad, motivo: str, usuario_id: int, nota: str | None = None,
        proveedor_id: int | None = None, orden_compra_id: int | None = None,
    ) -> StockNoVendible:
        """Pasa unidades de vendible a no vendible."""
        cantidad = _cantidad(cantidad)
        motivo_ok = _enum(MotivoNoVendible, motivo, "Motivo")
        if motivo_ok is None:
            raise SolicitudInvalida("Indicá el motivo: averiado, abollado, vencido, defecto de fábrica u otro")
        nota = _texto(nota)
        if motivo_ok == MotivoNoVendible.OTRO and not nota:
            raise SolicitudInvalida("Con el motivo 'otro' tenés que escribir una nota que lo explique")
        if proveedor_id is not None and self._proveedores.get_by_id(proveedor_id) is None:
            raise RecursoNoEncontrado("Proveedor", proveedor_id)
        if orden_compra_id is not None and not self._registros.existe_orden_compra(orden_compra_id):
            raise RecursoNoEncontrado("Orden de compra", orden_compra_id)

        producto = self._registros.bloquear_producto(producto_id)
        if producto is None:
            raise RecursoNoEncontrado("Producto", producto_id)
        if cantidad > producto.stock_actual:
            raise StockInsuficiente(producto.nombre, _fmt(producto.stock_actual), _fmt(cantidad))

        registro = self._registros.add(StockNoVendible(
            id=None, producto_id=producto_id, cantidad=cantidad, cantidad_pendiente=cantidad, motivo=motivo_ok,
            nota=nota, proveedor_id=proveedor_id, orden_compra_id=orden_compra_id,
            costo_unitario=producto.precio_compra, usuario_id=usuario_id,
        ))
        detalle = f"Pasa a no vendible ({ETIQUETA_MOTIVO[motivo_ok]})" + (f": {nota}" if nota else "")
        self._stock.mover(
            producto_id, delta_vendible=-cantidad, delta_no_vendible=cantidad,
            tipo=TipoMovimientoInventario.TRASPASO, cantidad=-cantidad,
            referencia_tipo=TipoReferenciaMovimiento.STOCK_NO_VENDIBLE, referencia_id=registro.id,
            usuario_id=usuario_id, observaciones=detalle,
        )
        return self.obtener(registro.id)

    def reparar(self, registro_id: int, cantidad, usuario_id: int, nota: str | None = None) -> StockNoVendible:
        """Las unidades se arreglaron: vuelven a stock vendible."""
        registro, cantidad = self._para_resolver(registro_id, cantidad)
        nota = _texto(nota)
        self._resolver(registro, TipoResolucionNoVendible.REPARADO, cantidad, 0, usuario_id, nota)
        self._stock.mover(
            registro.producto_id, delta_vendible=cantidad, delta_no_vendible=-cantidad,
            tipo=TipoMovimientoInventario.TRASPASO, cantidad=cantidad,
            referencia_tipo=TipoReferenciaMovimiento.STOCK_NO_VENDIBLE, referencia_id=registro.id,
            usuario_id=usuario_id, observaciones="Reparado: vuelve a stock vendible" + (f". {nota}" if nota else ""),
        )
        return self.obtener(registro.id)

    def descartar(self, registro_id: int, cantidad, usuario_id: int, nota: str | None = None) -> StockNoVendible:
        """Baja definitiva con pérdida (se tira, se rompe del todo, venció sin reclamo)."""
        registro, cantidad = self._para_resolver(registro_id, cantidad)
        nota = _texto(nota)
        perdida = int(round(cantidad * registro.costo_unitario))
        self._resolver(registro, TipoResolucionNoVendible.DESCARTADO, cantidad, perdida, usuario_id, nota)
        self._stock.mover(
            registro.producto_id, delta_vendible=Decimal("0"), delta_no_vendible=-cantidad,
            tipo=TipoMovimientoInventario.BAJA, cantidad=cantidad,
            referencia_tipo=TipoReferenciaMovimiento.STOCK_NO_VENDIBLE, referencia_id=registro.id,
            usuario_id=usuario_id, observaciones="Descarte: baja con pérdida" + (f". {nota}" if nota else ""),
        )
        return self.obtener(registro.id)

    def _para_resolver(self, registro_id: int, cantidad) -> tuple[StockNoVendible, Decimal]:
        registro = self._registros.get_by_id(registro_id, bloquear=True)
        if registro is None:
            raise RecursoNoEncontrado("Registro de stock no vendible", registro_id)
        if registro.estado == EstadoStockNoVendible.RESUELTO:
            raise TransicionDeEstadoInvalida("Estas unidades ya fueron resueltas por completo")
        libre = registro.cantidad_libre()
        cantidad = libre if cantidad is None else _cantidad(cantidad)
        if libre <= 0:
            raise TransicionDeEstadoInvalida(
                "Todas las unidades pendientes están en un reclamo al proveedor abierto: "
                "resolvelas desde el reclamo o sacalas del borrador"
            )
        if cantidad > libre:
            en_reclamo = f" ({_fmt(registro.cantidad_en_reclamo)} están en un reclamo abierto)" if registro.cantidad_en_reclamo else ""
            raise StockInsuficiente(f"{registro.producto_nombre} (no vendible){en_reclamo}", _fmt(libre), _fmt(cantidad))
        return registro, cantidad

    def _resolver(
        self, registro: StockNoVendible, tipo: TipoResolucionNoVendible, cantidad: Decimal, monto: int,
        usuario_id: int | None, nota: str | None, reclamo_id: int | None = None,
    ) -> None:
        registro.cantidad_pendiente -= cantidad
        if reclamo_id is not None:
            # Las unidades del ítem que se resuelve dejan de estar reservadas.
            registro.cantidad_en_reclamo = max(Decimal("0"), registro.cantidad_en_reclamo - cantidad)
        registro.recalcular_estado()
        self._registros.update(registro)
        self._registros.agregar_resolucion(ResolucionNoVendible(
            id=None, registro_id=registro.id, tipo=tipo, cantidad=cantidad, monto=monto,
            reclamo_id=reclamo_id, nota=nota, usuario_id=usuario_id,
        ))


class ReclamoProveedorService:
    def __init__(
        self, reclamos: ReclamoProveedorRepository, registros: StockNoVendibleRepository,
        movimientos: MovimientoInventarioRepository, proveedores: ProveedorRepository, empresa: EmpresaRepository,
    ):
        self._reclamos = reclamos
        self._registros = registros
        self._proveedores = proveedores
        self._empresa = empresa
        self._stock = _Stock(registros, movimientos)
        self._no_vendible = StockNoVendibleService(registros, movimientos, proveedores)

    # --- Consultas ------------------------------------------------------------------

    def listar(self, estado: str | None = None, proveedor_id: int | None = None) -> list[ReclamoProveedor]:
        estado_ok = _enum(EstadoReclamoProveedor, estado, "Estado")
        return self._reclamos.list(estado=estado_ok.value if estado_ok else None, proveedor_id=proveedor_id)

    def obtener(self, reclamo_id: int, bloquear: bool = False) -> ReclamoProveedor:
        reclamo = self._reclamos.get_by_id(reclamo_id, bloquear=bloquear)
        if reclamo is None:
            raise RecursoNoEncontrado("Reclamo", reclamo_id)
        return reclamo

    def documento(self, reclamo_id: int) -> tuple[Empresa, ReclamoProveedor]:
        """Datos para imprimir o enviar el reclamo: la empresa que reclama y el reclamo."""
        return self._empresa.get(), self.obtener(reclamo_id)

    # --- Borrador -------------------------------------------------------------------

    def crear(self, proveedor_id: int, items: list[dict], usuario_id: int, notas: str | None = None) -> ReclamoProveedor:
        proveedor = self._proveedores.get_by_id(proveedor_id)
        if proveedor is None:
            raise RecursoNoEncontrado("Proveedor", proveedor_id)
        lineas = self._armar_items(proveedor_id, items)
        reclamo = self._reclamos.add(ReclamoProveedor(
            id=None, numero=self._reclamos.siguiente_numero(), proveedor_id=proveedor_id, usuario_id=usuario_id,
            proveedor_razon_social=proveedor.razon_social, proveedor_ruc=proveedor.ruc,
            proveedor_telefono=proveedor.telefono, proveedor_email=proveedor.email,
            proveedor_direccion=", ".join(x for x in (proveedor.direccion, proveedor.ciudad) if x) or None,
            notas=_texto(notas), items=lineas,
        ))
        self._asociar_y_refrescar(proveedor_id, [i.registro_id for i in lineas])
        return self.obtener(reclamo.id)

    def actualizar(self, reclamo_id: int, items: list[dict], notas: str | None = None) -> ReclamoProveedor:
        reclamo = self.obtener(reclamo_id, bloquear=True)
        if not reclamo.puede_editarse():
            raise TransicionDeEstadoInvalida(f"Solo se edita un reclamo en borrador (este está {reclamo.estado.value})")
        anteriores = [i.registro_id for i in reclamo.items]
        lineas = self._armar_items(reclamo.proveedor_id, items, excluir_reclamo_id=reclamo.id)
        self._reclamos.replace_items(reclamo.id, lineas)
        reclamo.notas = _texto(notas)
        self._reclamos.update(reclamo)
        self._asociar_y_refrescar(reclamo.proveedor_id, anteriores + [i.registro_id for i in lineas])
        return self.obtener(reclamo.id)

    def eliminar(self, reclamo_id: int) -> None:
        reclamo = self.obtener(reclamo_id, bloquear=True)
        if not reclamo.puede_eliminarse():
            raise TransicionDeEstadoInvalida(
                "Solo se elimina un reclamo en borrador; uno enviado se cierra cuando el proveedor responde"
            )
        self._reclamos.delete(reclamo.id)
        self._refrescar([i.registro_id for i in reclamo.items])

    # --- Estados --------------------------------------------------------------------

    def enviar(self, reclamo_id: int, numero_nota_remision: str | None = None) -> ReclamoProveedor:
        reclamo = self.obtener(reclamo_id, bloquear=True)
        if not reclamo.puede_enviarse():
            raise TransicionDeEstadoInvalida(f"Solo se envía un reclamo en borrador con ítems (este está {reclamo.estado.value})")
        reclamo.estado = EstadoReclamoProveedor.ENVIADO
        reclamo.fecha_envio = self._registros.ahora()
        if _texto(numero_nota_remision):
            reclamo.numero_nota_remision = _texto(numero_nota_remision)
        return self._reclamos.update(reclamo)

    def aceptar(self, reclamo_id: int, respuesta_proveedor: str | None = None) -> ReclamoProveedor:
        reclamo = self.obtener(reclamo_id, bloquear=True)
        if not reclamo.puede_responderse():
            raise TransicionDeEstadoInvalida(f"Solo se acepta un reclamo enviado (este está {reclamo.estado.value})")
        reclamo.estado = EstadoReclamoProveedor.ACEPTADO
        reclamo.fecha_respuesta = self._registros.ahora()
        reclamo.respuesta_proveedor = _texto(respuesta_proveedor)
        return self._reclamos.update(reclamo)

    def rechazar(self, reclamo_id: int, motivo: str, usuario_id: int) -> ReclamoProveedor:
        """El proveedor rechaza todo el reclamo: las unidades siguen no vendibles
        (se pueden reparar, descartar o volver a reclamar)."""
        reclamo = self.obtener(reclamo_id, bloquear=True)
        if not reclamo.puede_responderse():
            raise TransicionDeEstadoInvalida(f"Solo se rechaza un reclamo enviado (este está {reclamo.estado.value})")
        motivo = _texto(motivo)
        if not motivo:
            raise SolicitudInvalida("Indicá el motivo del rechazo del proveedor")
        ahora = self._registros.ahora()
        for item in reclamo.items:
            if not item.esta_resuelto():
                item.resolucion = ResolucionItemReclamo.RECHAZADO
                item.resuelto_por, item.resuelto_at = usuario_id, ahora
        reclamo.estado = EstadoReclamoProveedor.RECHAZADO
        reclamo.fecha_respuesta = ahora
        reclamo.motivo_rechazo = motivo
        actualizado = self._reclamos.update(reclamo)
        self._refrescar([i.registro_id for i in reclamo.items])
        return actualizado

    def resolver_item(
        self, reclamo_id: int, item_id: int, resolucion: str, usuario_id: int,
        monto_nota_credito: int | None = None, nota: str | None = None, numero_nota_credito: str | None = None,
    ) -> ReclamoProveedor:
        reclamo = self.obtener(reclamo_id, bloquear=True)
        item = next((i for i in reclamo.items if i.id == item_id), None)
        if item is None:
            raise RecursoNoEncontrado("Ítem del reclamo", item_id)
        if item.esta_resuelto():
            raise TransicionDeEstadoInvalida(f"Este ítem ya fue resuelto ({item.resolucion.value})")
        if not reclamo.puede_resolver_items():
            raise TransicionDeEstadoInvalida(
                f"Los ítems se resuelven cuando el proveedor aceptó el reclamo (este está {reclamo.estado.value})"
            )
        tipo = _enum(ResolucionItemReclamo, resolucion, "Resolución")
        if tipo is None:
            raise SolicitudInvalida("Indicá la resolución: REPOSICION, NOTA_CREDITO o RECHAZADO")
        monto = 0
        if tipo == ResolucionItemReclamo.NOTA_CREDITO:
            if not monto_nota_credito or monto_nota_credito <= 0:
                raise SolicitudInvalida("Indicá el monto de la nota de crédito del proveedor")
            monto = int(monto_nota_credito)
        nota = _texto(nota)

        if tipo != ResolucionItemReclamo.RECHAZADO:
            registro = self._registros.get_by_id(item.registro_id, bloquear=True)
            if registro is None or registro.cantidad_pendiente < item.cantidad:
                raise TransicionDeEstadoInvalida("Las unidades de este ítem ya no están pendientes")
            tipo_resolucion = (
                TipoResolucionNoVendible.REPUESTO_PROVEEDOR if tipo == ResolucionItemReclamo.REPOSICION
                else TipoResolucionNoVendible.NOTA_CREDITO_PROVEEDOR
            )
            self._no_vendible._resolver(registro, tipo_resolucion, item.cantidad, monto, usuario_id, nota, reclamo_id=reclamo.id)
            comun = dict(referencia_tipo=TipoReferenciaMovimiento.RECLAMO_PROVEEDOR, referencia_id=reclamo.id, usuario_id=usuario_id)
            if tipo == ResolucionItemReclamo.REPOSICION:
                self._stock.mover(
                    item.producto_id, delta_vendible=Decimal("0"), delta_no_vendible=-item.cantidad,
                    tipo=TipoMovimientoInventario.SALIDA, cantidad=item.cantidad,
                    observaciones=f"Devuelto al proveedor para reposición ({reclamo.numero})", **comun,
                )
                self._stock.mover(
                    item.producto_id, delta_vendible=item.cantidad, delta_no_vendible=Decimal("0"),
                    tipo=TipoMovimientoInventario.ENTRADA, cantidad=item.cantidad,
                    observaciones=f"Reposición del proveedor ({reclamo.numero})", **comun,
                )
            else:
                self._stock.mover(
                    item.producto_id, delta_vendible=Decimal("0"), delta_no_vendible=-item.cantidad,
                    tipo=TipoMovimientoInventario.SALIDA, cantidad=item.cantidad,
                    observaciones=f"Devuelto al proveedor con nota de crédito ({reclamo.numero})", **comun,
                )

        item.resolucion = tipo
        item.monto_nota_credito = monto
        item.nota_resolucion = nota
        item.resuelto_por = usuario_id
        item.resuelto_at = self._registros.ahora()
        if _texto(numero_nota_credito):
            reclamo.numero_nota_credito = _texto(numero_nota_credito)
        if reclamo.todos_los_items_resueltos():
            reclamo.estado = EstadoReclamoProveedor.RESUELTO
            reclamo.fecha_resolucion = item.resuelto_at
        actualizado = self._reclamos.update(reclamo)
        self._refrescar([item.registro_id])
        return actualizado

    def actualizar_documentos(self, reclamo_id: int, **numeros: str | None) -> ReclamoProveedor:
        """Registra los números de la nota de crédito del proveedor y de la nota
        de remisión del traslado (SAIL no emite documentos fiscales). Solo
        cambia los campos que se mandan; un texto vacío los borra."""
        reclamo = self.obtener(reclamo_id, bloquear=True)
        for campo in ("numero_nota_credito", "numero_nota_remision"):
            if campo in numeros:
                setattr(reclamo, campo, _texto(numeros[campo]))
        return self._reclamos.update(reclamo)

    # --- Auxiliares -----------------------------------------------------------------

    def _armar_items(
        self, proveedor_id: int | None, items: list[dict], excluir_reclamo_id: int | None = None,
    ) -> list[ReclamoProveedorItem]:
        if not items:
            raise SolicitudInvalida("El reclamo tiene que tener al menos un ítem")
        ids = [int(i["registro_id"]) for i in items]
        if len(set(ids)) != len(ids):
            raise SolicitudInvalida("Hay unidades repetidas en el reclamo: cada registro va una sola vez")
        registros = {r.id: r for r in self._registros.get_many(ids, bloquear=True)}
        en_otros = self._registros.cantidades_en_reclamo(ids, excluir_reclamo_id=excluir_reclamo_id)
        lineas = []
        for dato in items:
            registro = registros.get(int(dato["registro_id"]))
            if registro is None:
                raise RecursoNoEncontrado("Registro de stock no vendible", dato["registro_id"])
            nombre = registro.producto_nombre
            if registro.estado == EstadoStockNoVendible.RESUELTO:
                raise SolicitudInvalida(f"Las unidades de {nombre} (registro {registro.id}) ya fueron resueltas")
            if registro.proveedor_id is not None and registro.proveedor_id != proveedor_id:
                raise SolicitudInvalida(
                    f"Las unidades de {nombre} (registro {registro.id}) son de otro proveedor ({registro.proveedor_nombre})"
                )
            libre = Decimal(registro.cantidad_pendiente) - en_otros.get(registro.id, Decimal("0"))
            if libre <= 0:
                raise SolicitudInvalida(f"Las unidades de {nombre} (registro {registro.id}) ya están en otro reclamo abierto")
            cantidad = libre if dato.get("cantidad") is None else _cantidad(dato["cantidad"])
            if cantidad > libre:
                raise SolicitudInvalida(
                    f"De {nombre} (registro {registro.id}) quedan {_fmt(libre)} unidades para reclamar; pediste {_fmt(cantidad)}"
                )
            lineas.append(ReclamoProveedorItem(
                id=None, reclamo_id=None, registro_id=registro.id, producto_id=registro.producto_id,
                cantidad=cantidad, costo_unitario=registro.costo_unitario,
            ))
        return lineas

    def _asociar_y_refrescar(self, proveedor_id: int | None, registro_ids: list[int]) -> None:
        """Las unidades reclamadas quedan asociadas al proveedor del reclamo."""
        for registro in self._registros.get_many(sorted(set(registro_ids))):
            if registro.proveedor_id is None and proveedor_id is not None:
                registro.proveedor_id = proveedor_id
            registro.recalcular_estado()
            self._registros.update(registro)

    def _refrescar(self, registro_ids: list[int]) -> None:
        self._asociar_y_refrescar(None, registro_ids)
