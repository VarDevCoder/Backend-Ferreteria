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
from sqlalchemy.orm import Session

from app.infrastructure.db.models import (
    CajaTurnoModel,
    ClienteModel,
    MovimientoCajaModel,
    MovimientoCuentaCorrienteModel,
    MovimientoInventarioModel,
    ProductoModel,
    VentaMostradorItemModel,
    VentaMostradorModel,
    VentaPagoModel,
)

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

    # Reloj de la base (el mismo que usa la app para "hoy").
    ahora: datetime = db.execute(select(func.now())).scalar_one().replace(tzinfo=None)
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
    momento_inicial = datetime.combine(inicio, time(7, 0))
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

    # 3) Turnos y ventas.
    turno_abierto = db.execute(select(CajaTurnoModel).where(CajaTurnoModel.estado == "ABIERTO")).scalars().first()
    turnos: dict = {}
    creadas = 0
    for momento, items, metodo, cliente, descuento in plan:
        dia = momento.date()
        turno = turnos.get(dia)
        if turno is None:
            if dia == hoy and turno_abierto is not None:
                turno = turno_abierto
            else:
                turno = CajaTurnoModel(
                    usuario_id=vendedor_id, fondo_inicial=FONDO_INICIAL, estado="ABIERTO",
                    fecha_apertura=datetime.combine(dia, time(7, 25)) if dia != hoy else min(momento, ahora) - timedelta(minutes=20),
                    total_ventas_efectivo=0, total_ventas_tarjeta=0, total_ventas_transferencia=0, total_ventas_a_cuenta=0,
                )
                db.add(turno)
                db.flush()
            turnos[dia] = turno

        subtotal = sum(int(p.precio_venta) * cantidad for p, cantidad in items)
        total = max(0, subtotal - round(subtotal * descuento / 100))
        venta = VentaMostradorModel(
            numero=f"TMP-DEMO-{creadas}", caja_turno_id=turno.id, usuario_id=vendedor_id, cliente_id=cliente,
            metodo_pago=metodo, subtotal=subtotal, descuento=descuento, total=total, created_at=momento,
        )
        venta.items = [
            VentaMostradorItemModel(producto_id=p.id, cantidad=cantidad, precio_unitario=int(p.precio_venta), subtotal=int(p.precio_venta) * cantidad)
            for p, cantidad in items
        ]
        venta.pagos = [VentaPagoModel(metodo=metodo, monto=total)]
        db.add(venta)
        db.flush()
        for p, cantidad in items:
            anterior = stock_en_curso[p.id]
            stock_en_curso[p.id] = anterior - cantidad
            db.add(MovimientoInventarioModel(
                producto_id=p.id, tipo="SALIDA", cantidad=cantidad, stock_anterior=anterior, stock_nuevo=stock_en_curso[p.id],
                referencia_tipo="VENTA_MOSTRADOR", referencia_id=venta.id, usuario_id=vendedor_id,
                observaciones="Venta de mostrador", created_at=momento,
            ))
        campo = _campo_del_turno(metodo)
        setattr(turno, campo, (getattr(turno, campo) or 0) + total)
        creadas += 1

    # 4) Cierre de turnos pasados: algún retiro y arqueo.
    for dia, turno in turnos.items():
        if dia == hoy:
            continue
        retiro = 0
        if (turno.total_ventas_efectivo or 0) > 1_000_000 and rng.random() < 0.5:
            retiro = 500_000
            db.add(MovimientoCajaModel(
                caja_turno_id=turno.id, tipo="RETIRO", monto=retiro, motivo="Depósito en banco", usuario_id=usuario_id,
                created_at=datetime.combine(dia, time(14, 0)),
            ))
        esperado = FONDO_INICIAL + (turno.total_ventas_efectivo or 0) - retiro
        diferencia = rng.choice([0] * 9 + [-5_000, 2_000])
        turno.estado = "CERRADO"
        turno.fecha_cierre = datetime.combine(dia, time(18, 45))
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
            SELECT id, EXTRACT(YEAR FROM created_at)::int AS anio,
                   ROW_NUMBER() OVER (PARTITION BY EXTRACT(YEAR FROM created_at) ORDER BY created_at, id) AS correlativo
            FROM ventas_mostrador
        ) n
        WHERE v.id = n.id
    """))
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
        select(VentaMostradorModel).where(VentaMostradorModel.metodo_pago.in_(NO_EFECTIVO)).order_by(VentaMostradorModel.created_at)
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
