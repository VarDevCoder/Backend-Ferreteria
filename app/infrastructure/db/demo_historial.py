"""Historial de ventas para la base de DEMOSTRACIÓN (nunca para un cliente real).

Una demo con "0 ventas" no vende el sistema. Esto genera varias semanas de
operación creíble de una ferretería:

- un turno de caja por día hábil (lunes a sábado), con fondo inicial,
  algún retiro de efectivo y arqueo al cierre (casi siempre exacto, a veces
  con una diferencia chica, como pasa en la realidad);
- ventas de mostrador repartidas en el horario comercial, con productos de
  rotación alta más frecuentes, efectivo, tarjeta de débito o crédito,
  transferencia o QR y, a veces, cliente registrado o descuento;
- clientes con cuenta corriente: ventas a cuenta (todo o una parte), cobros
  posteriores y deudas de distinta antigüedad (ver `completar_medios_de_pago`);
- stock coherente: el inventario inicial alcanza para lo vendido y el kardex
  registra cada salida; algunos productos terminan bajo el mínimo, para que
  la demo muestre las alertas de reposición;
- el turno de hoy queda abierto con ventas, así el Inicio muestra "vendido hoy".

Se ejecuta solo si no hay ventas anteriores a la última semana (las pruebas
que se hagan en la demo no lo bloquean) y es reproducible (semilla fija).
Inserta directo en las tablas porque necesita fechas pasadas, que los casos
de uso no permiten a propósito.
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.core.tiempo import local_a_utc, zona
from app.infrastructure.db.models import (
    CajaTurnoModel,
    ClienteModel,
    MovimientoCajaModel,
    MovimientoCuentaCorrienteModel,
    MovimientoInventarioModel,
    ProductoModel,
    ProveedorModel,
    ReclamoProveedorItemModel,
    ReclamoProveedorModel,
    ResolucionNoVendibleModel,
    StockNoVendibleModel,
    UsuarioModel,
    VentaMostradorItemModel,
    VentaMostradorModel,
    VentaPagoModel,
)
from app.infrastructure.db.repositories.stock_no_vendible_repository import SqlAlchemyReclamoProveedorRepository

DIAS_DE_HISTORIAL = 42
FONDO_INICIAL = 300_000
MEDIOS_DE_PAGO = [("EFECTIVO", 52), ("TARJETA_DEBITO", 18), ("TARJETA_CREDITO", 12), ("TRANSFERENCIA", 12), ("QR", 6)]
NO_EFECTIVO = ("TARJETA", "TARJETA_DEBITO", "TARJETA_CREDITO", "TRANSFERENCIA", "QR")


def _campo_del_turno(metodo: str) -> str:
    """En qué total del turno se acumula cada medio (igual que `acumular_venta`)."""
    if metodo == "EFECTIVO":
        return "total_ventas_efectivo"
    if metodo.startswith("TARJETA"):
        return "total_ventas_tarjeta"
    if metodo == "CUENTA_CORRIENTE":
        return "total_ventas_a_cuenta"
    return "total_ventas_transferencia"


def hay_historial(db: Session) -> bool:
    hace_una_semana = db.execute(select(func.now() - timedelta(days=7))).scalar_one()
    anteriores = db.execute(
        select(func.count()).select_from(VentaMostradorModel).where(VentaMostradorModel.created_at < hace_una_semana)
    ).scalar_one()
    return anteriores > 0


def _peso_de_venta(producto: ProductoModel) -> float:
    """Lo barato rota más: cinta teflón y tornillos salen todos los días; un taladro, poco."""
    return max(0.3, 6 - min(5.5, producto.precio_venta / 80_000))


def _cantidad(producto: ProductoModel, rng: random.Random) -> int:
    if producto.precio_venta < 10_000:
        return rng.choice([1, 2, 2, 3, 4, 5, 6, 10])
    if producto.precio_venta < 60_000:
        return rng.choice([1, 1, 2, 2, 3, 4])
    return rng.choice([1, 1, 1, 2])


def generar_historial(db: Session, usuario_id: int, vendedor_id: int | None = None, semilla: int = 2026) -> int:
    """Genera el historial y devuelve cuántas ventas creó (0 si ya había)."""
    if hay_historial(db):
        return 0

    rng = random.Random(semilla)
    vendedor_id = vendedor_id or usuario_id
    productos = db.execute(select(ProductoModel).where(ProductoModel.activo.is_(True))).scalars().all()
    if not productos:
        return 0
    clientes = db.execute(select(ClienteModel.id).where(ClienteModel.activo.is_(True))).scalars().all()
    pesos = [_peso_de_venta(p) for p in productos]

    # Reloj de la base, en la hora de la ferretería: el plan (días, horario de
    # 7:30 a 18:30) se arma en hora local y se guarda en UTC (local_a_utc),
    # como todo `created_at`.
    ahora: datetime = db.execute(select(func.now())).scalar_one().astimezone(zona()).replace(tzinfo=None)
    hoy = ahora.date()
    inicio = hoy - timedelta(days=DIAS_DE_HISTORIAL)

    # 1) Planificar todas las ventas por día.
    plan: list[tuple[datetime, list[tuple[ProductoModel, int]], str, int | None, int]] = []
    for desplazamiento in range(DIAS_DE_HISTORIAL + 1):
        dia = inicio + timedelta(days=desplazamiento)
        if dia.weekday() == 6:  # domingo cerrado
            continue
        apertura = datetime.combine(dia, time(7, 30))
        cierre = datetime.combine(dia, time(18, 30))
        if dia == hoy:
            cierre = min(cierre, ahora - timedelta(minutes=5))
            if cierre <= apertura:  # la demo se mira de madrugada: ventas en las últimas horas
                apertura, cierre = ahora - timedelta(hours=3), ahora - timedelta(minutes=5)
        cantidad_ventas = rng.randint(8, 18) if dia.weekday() == 5 else rng.randint(6, 14)
        if dia == hoy:
            cantidad_ventas = rng.randint(4, 8)
        segundos = int((cierre - apertura).total_seconds())
        for momento in sorted(apertura + timedelta(seconds=rng.randint(0, segundos)) for _ in range(cantidad_ventas)):
            elegidos = rng.choices(productos, weights=pesos, k=rng.choice([1, 1, 2, 2, 3, 4]))
            items: dict[int, tuple[ProductoModel, int]] = {}
            for p in elegidos:
                cantidad_previa = items.get(p.id, (p, 0))[1]
                items[p.id] = (p, cantidad_previa + _cantidad(p, rng))
            metodo = rng.choices([m for m, _ in MEDIOS_DE_PAGO], weights=[w for _, w in MEDIOS_DE_PAGO])[0]
            cliente = rng.choice(clientes) if clientes and rng.random() < 0.2 else None
            descuento = rng.choice([5, 10]) if rng.random() < 0.08 else 0
            plan.append((momento, list(items.values()), metodo, cliente, descuento))

    # 2) Stock inicial que alcance para todo lo vendido y deje algunos productos bajo el mínimo.
    vendido: dict[int, Decimal] = {}
    for _, items, *_ in plan:
        for p, cantidad in items:
            vendido[p.id] = vendido.get(p.id, Decimal(0)) + cantidad
    momento_inicial = local_a_utc(datetime.combine(inicio, time(7, 0)))
    # Los movimientos que ya existían (p. ej. el inventario inicial del seed,
    # fechado hoy) pasan a antes del historial, conservando su orden: si no,
    # el kardex quedaría desordenado respecto del stock.
    db.execute(
        text("""UPDATE movimientos_inventario
                SET created_at = CAST(:antes AS timestamp) + (id * INTERVAL '1 second')
                WHERE created_at >= CAST(:inicio AS timestamp)"""),
        {"antes": momento_inicial - timedelta(days=1), "inicio": momento_inicial},
    )
    stock_en_curso: dict[int, Decimal] = {}
    for p in productos:
        minimo = Decimal(p.stock_minimo or 0)
        final = (minimo * Decimal(rng.choice(["0.5", "0.8", "1.5", "2", "3", "4"]))).quantize(Decimal(1)) if minimo else Decimal(rng.randint(5, 30))
        inicial = vendido.get(p.id, Decimal(0)) + final
        anterior = Decimal(p.stock_actual or 0)
        if inicial != anterior:
            db.add(MovimientoInventarioModel(
                producto_id=p.id, tipo="AJUSTE", cantidad=inicial - anterior, stock_anterior=anterior, stock_nuevo=inicial,
                referencia_tipo="AJUSTE_MANUAL", referencia_id=p.id, usuario_id=usuario_id,
                observaciones="Inventario inicial (demo)", created_at=momento_inicial,
            ))
        stock_en_curso[p.id] = inicial

    # 3) Turnos y ventas. Todo se inserta en lotes (pocas idas y vueltas a la
    #    base): en Vercel cada consulta viaja hasta Neon y el arranque tiene
    #    tiempo limitado.
    turno_abierto = db.execute(select(CajaTurnoModel).where(CajaTurnoModel.estado == "ABIERTO")).scalars().first()
    turnos: dict = {}
    for momento, *_ in plan:
        dia = momento.date()
        if dia in turnos:
            continue
        if dia == hoy and turno_abierto is not None:
            turnos[dia] = turno_abierto
        else:
            turnos[dia] = CajaTurnoModel(
                usuario_id=vendedor_id, fondo_inicial=FONDO_INICIAL, estado="ABIERTO",
                fecha_apertura=local_a_utc(datetime.combine(dia, time(7, 25)) if dia != hoy else min(momento, ahora) - timedelta(minutes=20)),
                total_ventas_efectivo=0, total_ventas_tarjeta=0, total_ventas_transferencia=0, total_ventas_a_cuenta=0,
            )
            db.add(turnos[dia])
    db.flush()

    ventas: list[tuple[VentaMostradorModel, list[tuple[ProductoModel, int]]]] = []
    for creadas, (momento, items, metodo, cliente, descuento) in enumerate(plan):
        turno = turnos[momento.date()]
        subtotal = sum(int(p.precio_venta) * cantidad for p, cantidad in items)
        total = max(0, subtotal - round(subtotal * descuento / 100))
        venta = VentaMostradorModel(
            numero=f"TMP-DEMO-{creadas}", caja_turno_id=turno.id, usuario_id=vendedor_id, cliente_id=cliente,
            metodo_pago=metodo, subtotal=subtotal, descuento=descuento, total=total, created_at=local_a_utc(momento),
        )
        venta.items = [
            VentaMostradorItemModel(producto_id=p.id, cantidad=cantidad, precio_unitario=int(p.precio_venta), subtotal=int(p.precio_venta) * cantidad)
            for p, cantidad in items
        ]
        venta.pagos = [VentaPagoModel(metodo=metodo, monto=total)]
        db.add(venta)
        ventas.append((venta, items))
        campo = _campo_del_turno(metodo)
        setattr(turno, campo, (getattr(turno, campo) or 0) + total)
    db.flush()  # inserta ventas, ítems y pagos en lotes y asigna los id

    for venta, items in ventas:  # el plan ya está en orden cronológico
        for p, cantidad in items:
            anterior = stock_en_curso[p.id]
            stock_en_curso[p.id] = anterior - cantidad
            db.add(MovimientoInventarioModel(
                producto_id=p.id, tipo="SALIDA", cantidad=cantidad, stock_anterior=anterior, stock_nuevo=stock_en_curso[p.id],
                referencia_tipo="VENTA_MOSTRADOR", referencia_id=venta.id, usuario_id=vendedor_id,
                observaciones="Venta de mostrador", created_at=venta.created_at,
            ))
    creadas = len(ventas)

    # 4) Cierre de turnos pasados: algún retiro y arqueo.
    for dia, turno in turnos.items():
        if dia == hoy:
            continue
        retiro = 0
        if (turno.total_ventas_efectivo or 0) > 1_000_000 and rng.random() < 0.5:
            retiro = 500_000
            db.add(MovimientoCajaModel(
                caja_turno_id=turno.id, tipo="RETIRO", monto=retiro, motivo="Depósito en banco", usuario_id=usuario_id,
                created_at=local_a_utc(datetime.combine(dia, time(14, 0))),
            ))
        esperado = FONDO_INICIAL + (turno.total_ventas_efectivo or 0) - retiro
        diferencia = rng.choice([0] * 9 + [-5_000, 2_000])
        turno.estado = "CERRADO"
        turno.fecha_cierre = local_a_utc(datetime.combine(dia, time(18, 45)))
        turno.conteo_fisico = esperado + diferencia
        turno.diferencia = diferencia

    for p in productos:
        p.stock_actual = stock_en_curso[p.id]
    db.flush()

    # 5) Numeración correlativa por año en orden cronológico (VTA-AAAA-NNNN),
    #    incluidas las ventas de prueba que ya hubiera. En dos pasos por el UNIQUE.
    db.execute(text("UPDATE ventas_mostrador SET numero = 'TMP-' || id"))
    db.execute(text("""
        UPDATE ventas_mostrador v
        SET numero = 'VTA-' || n.anio || '-' || LPAD(n.correlativo::text, 4, '0')
        FROM (
            SELECT id, EXTRACT(YEAR FROM timezone(:zona, timezone('UTC', created_at)))::int AS anio,
                   ROW_NUMBER() OVER (
                       PARTITION BY EXTRACT(YEAR FROM timezone(:zona, timezone('UTC', created_at)))
                       ORDER BY created_at, id
                   ) AS correlativo
            FROM ventas_mostrador
        ) n
        WHERE v.id = n.id
    """), {"zona": zona().key})
    return creadas


# --- Medios de pago y cuenta corriente --------------------------------------------

# (nombre del cliente, límite de crédito, probabilidad de que pague cada compra).
# Los que no estén en la base se ignoran. Juan paga poco: deja deuda atrasada.
CLIENTES_CON_CREDITO = [
    ("Constructora Mbaretê S.R.L.", 8_000_000, 0.8),
    ("Electricista Ramón Ortiz", 2_500_000, 0.7),
    ("Juan Benítez", 1_500_000, 0.15),
]


def _cambiar_pagos(venta: VentaMostradorModel, turno: CajaTurnoModel, pagos: list[tuple[str, int]]) -> None:
    """Reemplaza los pagos de una venta y corrige los totales del turno.
    Solo se usa con ventas no cobradas en efectivo: el arqueo no cambia."""
    for p in venta.pagos:
        campo = _campo_del_turno(p.metodo)
        setattr(turno, campo, (getattr(turno, campo) or 0) - p.monto)
    venta.pagos = [VentaPagoModel(metodo=m, monto=monto) for m, monto in pagos]
    for m, monto in pagos:
        campo = _campo_del_turno(m)
        setattr(turno, campo, (getattr(turno, campo) or 0) + monto)
    venta.metodo_pago = pagos[0][0] if len(pagos) == 1 else "MIXTO"


def completar_medios_de_pago(db: Session, usuario_id: int, semilla: int = 2026) -> int:
    """Lleva el historial de la demo a los medios de pago actuales.

    Sirve tanto para una base nueva como para la demo que ya tenía ventas:
    - las ventas con la "TARJETA" genérica pasan a débito o crédito;
    - algunas ventas con tarjeta se pagan en parte por QR o transferencia (pago mixto);
    - algunos clientes reciben límite de crédito y compran a cuenta, con
      cobros posteriores, así hay deudas al día y otras atrasadas.
    Solo toca ventas no cobradas en efectivo, así los arqueos siguen cerrando.
    Corre una sola vez: si ya hay movimientos de cuenta corriente, no hace nada.
    Devuelve cuántas ventas a cuenta generó.
    """
    if db.execute(select(func.count()).select_from(MovimientoCuentaCorrienteModel)).scalar_one():
        return 0
    rng = random.Random(semilla + 1)
    ahora: datetime = db.execute(select(func.now())).scalar_one().replace(tzinfo=None)

    ventas = db.execute(
        select(VentaMostradorModel)
        .where(VentaMostradorModel.metodo_pago.in_(NO_EFECTIVO))
        .options(selectinload(VentaMostradorModel.pagos))
        .order_by(VentaMostradorModel.created_at)
    ).scalars().all()
    turnos = {t.id: t for t in db.execute(select(CajaTurnoModel)).scalars()}

    # 1) Tarjeta genérica -> débito / crédito.
    for venta in ventas:
        if venta.metodo_pago == "TARJETA":
            _cambiar_pagos(venta, turnos[venta.caja_turno_id], [(rng.choice(["TARJETA_DEBITO"] * 3 + ["TARJETA_CREDITO"] * 2), venta.total)])

    # 2) Clientes con crédito.
    nombres = {nombre: limite for nombre, limite, _ in CLIENTES_CON_CREDITO}
    paga = {nombre: probabilidad for nombre, _, probabilidad in CLIENTES_CON_CREDITO}
    clientes = [c for c in db.execute(select(ClienteModel).where(ClienteModel.nombre.in_(nombres))).scalars()]
    for c in clientes:
        c.limite_credito = nombres[c.nombre]

    # 3) Ventas a cuenta (completas o con entrega) y cobros posteriores.
    saldos = {c.id: 0 for c in clientes}
    cobros: list[tuple[datetime, ClienteModel, int]] = []
    creadas = 0
    candidatas = [v for v in ventas if 80_000 <= v.total <= 2_500_000]
    # Más compras a cuenta en los primeros días, así hay deudas de más de 30 días.
    primeros_dias = candidatas[0].created_at + timedelta(days=10) if candidatas else ahora
    for venta in candidatas:
        if not clientes or rng.random() > (0.3 if venta.created_at < primeros_dias else 0.1):
            continue
        # Cobros ya ocurridos antes de esta venta.
        for fecha, cliente, monto in [c for c in cobros if c[0] <= venta.created_at]:
            saldos[cliente.id] -= monto
            cobros.remove((fecha, cliente, monto))
            db.add(MovimientoCuentaCorrienteModel(
                cliente_id=cliente.id, tipo="PAGO", monto=monto, metodo_pago="TRANSFERENCIA",
                referencia="Transferencia bancaria", usuario_id=usuario_id, created_at=fecha,
            ))
        cliente = rng.choice(clientes)
        entrega = (venta.total // 3 // 1000) * 1000 if rng.random() < 0.4 else 0
        a_cuenta = venta.total - entrega
        if saldos[cliente.id] + a_cuenta > cliente.limite_credito:
            continue
        metodo_entrega = venta.pagos[0].metodo if venta.pagos else "TRANSFERENCIA"
        pagos = ([(metodo_entrega, entrega)] if entrega else []) + [("CUENTA_CORRIENTE", a_cuenta)]
        _cambiar_pagos(venta, turnos[venta.caja_turno_id], pagos)
        venta.cliente_id = cliente.id
        saldos[cliente.id] += a_cuenta
        db.add(MovimientoCuentaCorrienteModel(
            cliente_id=cliente.id, tipo="CARGO", monto=a_cuenta, venta_id=venta.id, caja_turno_id=venta.caja_turno_id,
            referencia="Venta (a cuenta)", usuario_id=venta.usuario_id, created_at=venta.created_at,
        ))
        creadas += 1
        # La mayoría paga a las 1-3 semanas; algunos dejan la deuda.
        fecha_cobro = venta.created_at + timedelta(days=rng.randint(7, 21), hours=rng.randint(0, 5))
        if rng.random() < paga[cliente.nombre] and fecha_cobro < ahora:
            parte = a_cuenta if rng.random() < 0.7 else (a_cuenta // 2 // 1000) * 1000
            cobros.append((fecha_cobro, cliente, parte))
    for fecha, cliente, monto in cobros:
        db.add(MovimientoCuentaCorrienteModel(
            cliente_id=cliente.id, tipo="PAGO", monto=monto, metodo_pago="TRANSFERENCIA",
            referencia="Transferencia bancaria", usuario_id=usuario_id, created_at=fecha,
        ))

    # 4) Algunos pagos mixtos: parte con tarjeta y parte por QR o transferencia.
    for venta in ventas:
        if len(venta.pagos) == 1 and venta.pagos[0].metodo.startswith("TARJETA") and venta.total >= 100_000 and rng.random() < 0.15:
            otra = (venta.total * rng.choice([3, 4, 5]) // 10 // 1000) * 1000
            _cambiar_pagos(venta, turnos[venta.caja_turno_id], [(venta.pagos[0].metodo, venta.total - otra), (rng.choice(["QR", "TRANSFERENCIA"]), otra)])

    # Las referencias de los cargos llevan el número de la venta.
    db.flush()
    db.execute(text("""
        UPDATE movimientos_cuenta_corriente m SET referencia = 'Venta ' || v.numero
        FROM ventas_mostrador v WHERE m.venta_id = v.id
    """))
    return creadas


# --- Stock no vendible y reclamo al proveedor ---------------------------------------

# (producto, cantidad, motivo, nota, proveedor, va al reclamo, unidades ya descartadas)
CASOS_NO_VENDIBLES = [
    ("Taladro percutor 1/2\"", 1, "DEFECTO_FABRICA", "No enciende; está en garantía", "Distribuidora Central Ferretera", True, 0),
    ("Martillo carpintero 16oz", 2, "DEFECTO_FABRICA", "Mango rajado de fábrica", "Distribuidora Central Ferretera", True, 0),
    ("Pintura látex exterior 4L", 3, "ABOLLADO", "Latas golpeadas en la descarga", None, False, 0),
    ("Silicona transparente 280ml", 4, "VENCIDO", None, None, False, 0),
    ("Llave térmica 20A", 2, "AVERIADO", "Se cayeron del estante", "ElectroPar Mayorista", False, 0),
    ("Foco LED 12W", 5, "AVERIADO", "Vidrio roto", None, False, 2),
]
ETIQUETA_MOTIVO = {"AVERIADO": "averiado", "ABOLLADO": "abollado", "VENCIDO": "vencido", "DEFECTO_FABRICA": "defecto de fábrica"}


def cargar_stock_no_vendible(db: Session, usuario_id: int) -> int:
    """Algunas unidades no vendibles (averiadas, abolladas, vencidas, con
    defecto de fábrica; una con parte ya descartada) y un reclamo ENVIADO a un
    proveedor. Corre una sola vez (si ya hay registros no hace nada) y usa
    pocas consultas: cada tabla se inserta en un solo lote. Los movimientos
    quedan con la hora actual, después de todo el historial, para que el
    kardex siga cuadrando. Devuelve cuántos registros creó."""
    if db.execute(select(func.count()).select_from(StockNoVendibleModel)).scalar_one():
        return 0
    nombres = [caso[0] for caso in CASOS_NO_VENDIBLES]
    productos = {
        p.nombre: p
        for p in db.execute(select(ProductoModel).where(ProductoModel.nombre.in_(nombres)).with_for_update()).scalars()
    }
    proveedores = {
        prov.razon_social: (prov, email)
        for prov, email in db.execute(
            select(ProveedorModel, UsuarioModel.email).join(UsuarioModel, UsuarioModel.id == ProveedorModel.user_id)
        ).all()
    }

    casos = []
    for nombre, cantidad, motivo, nota, proveedor, reclamar, descartadas in CASOS_NO_VENDIBLES:
        producto = productos.get(nombre)
        cantidad = min(Decimal(cantidad), Decimal(producto.stock_actual or 0)) if producto else Decimal(0)
        if cantidad <= 0:
            continue
        prov = proveedores.get(proveedor, (None, None))[0] if proveedor else None
        descartadas = min(Decimal(descartadas), cantidad)
        registro = StockNoVendibleModel(
            producto_id=producto.id, cantidad=cantidad, cantidad_pendiente=cantidad - descartadas, motivo=motivo,
            nota=nota, proveedor_id=prov.id if prov else None, costo_unitario=producto.precio_compra,
            estado="EN_RECLAMO" if reclamar and prov else ("RESUELTO" if descartadas == cantidad else "PENDIENTE"),
            usuario_id=usuario_id,
        )
        casos.append((producto, registro, prov if reclamar else None, descartadas))
    if not casos:
        return 0
    db.add_all([registro for _, registro, _, _ in casos])
    db.flush()  # un INSERT con todos los registros

    movimientos, resoluciones, nuevos_stocks = [], [], []
    for producto, registro, _, descartadas in casos:
        vendible, no_vendible = Decimal(producto.stock_actual), Decimal(producto.stock_no_vendible or 0)
        detalle = f"Pasa a no vendible ({ETIQUETA_MOTIVO[registro.motivo]})" + (f": {registro.nota}" if registro.nota else "")
        movimientos.append(MovimientoInventarioModel(
            producto_id=producto.id, tipo="TRASPASO", cantidad=-registro.cantidad, stock_anterior=vendible,
            stock_nuevo=vendible - registro.cantidad, no_vendible_anterior=no_vendible,
            no_vendible_nuevo=no_vendible + registro.cantidad, referencia_tipo="STOCK_NO_VENDIBLE",
            referencia_id=registro.id, usuario_id=usuario_id, observaciones=detalle,
        ))
        vendible, no_vendible = vendible - registro.cantidad, no_vendible + registro.cantidad
        if descartadas:
            movimientos.append(MovimientoInventarioModel(
                producto_id=producto.id, tipo="BAJA", cantidad=descartadas, stock_anterior=vendible, stock_nuevo=vendible,
                no_vendible_anterior=no_vendible, no_vendible_nuevo=no_vendible - descartadas,
                referencia_tipo="STOCK_NO_VENDIBLE", referencia_id=registro.id, usuario_id=usuario_id,
                observaciones="Descarte: baja con pérdida. Sin arreglo posible",
            ))
            resoluciones.append(ResolucionNoVendibleModel(
                registro_id=registro.id, tipo="DESCARTADO", cantidad=descartadas,
                monto=int(descartadas * registro.costo_unitario), nota="Sin arreglo posible", usuario_id=usuario_id,
            ))
            no_vendible -= descartadas
        nuevos_stocks.append((producto.id, vendible, no_vendible))

    # Reclamo enviado al proveedor con las unidades de defecto de fábrica.
    reclamar = [(producto, registro, prov) for producto, registro, prov, _ in casos if prov is not None]
    if reclamar:
        prov = reclamar[0][2]
        email = proveedores[prov.razon_social][1]
        ahora = db.execute(select(func.now())).scalar_one().replace(tzinfo=None)
        db.add(ReclamoProveedorModel(
            numero=SqlAlchemyReclamoProveedorRepository(db).siguiente_numero(), proveedor_id=prov.id,
            usuario_id=usuario_id, proveedor_razon_social=prov.razon_social, proveedor_ruc=prov.ruc,
            proveedor_telefono=prov.telefono, proveedor_email=email,
            proveedor_direccion=", ".join(x for x in (prov.direccion, prov.ciudad) if x) or None,
            estado="ENVIADO", notas="Unidades con defecto de fábrica de la última compra (demo)",
            numero_nota_remision="001-001-0000457", fecha_envio=ahora,
            items=[
                ReclamoProveedorItemModel(
                    registro_id=registro.id, producto_id=producto.id, cantidad=registro.cantidad_pendiente,
                    costo_unitario=registro.costo_unitario, monto_nota_credito=0,
                )
                for producto, registro, p in reclamar if p.id == prov.id
            ],
        ))
    db.add_all(movimientos + resoluciones)
    db.flush()  # INSERT en lote de movimientos, resoluciones, reclamo e ítems

    # Stock de todos los productos en un solo UPDATE.
    valores, parametros = [], {}
    for n, (producto_id, vendible, no_vendible) in enumerate(nuevos_stocks):
        valores.append(f"(CAST(:id{n} AS integer), CAST(:v{n} AS numeric), CAST(:nv{n} AS numeric))")
        parametros.update({f"id{n}": producto_id, f"v{n}": vendible, f"nv{n}": no_vendible})
    db.execute(text(f"""
        UPDATE productos p SET stock_actual = s.vendible, stock_no_vendible = s.no_vendible
        FROM (VALUES {", ".join(valores)}) AS s(id, vendible, no_vendible) WHERE p.id = s.id
    """), parametros)
    for producto, *_ in casos:
        db.expire(producto)
    return len(casos)
