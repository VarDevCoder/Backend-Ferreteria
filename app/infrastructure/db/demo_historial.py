"""Historial de ventas para la base de DEMOSTRACIÓN (nunca para un cliente real).

Una demo con "0 ventas" no vende el sistema. Esto genera varias semanas de
operación creíble de una ferretería:

- un turno de caja por día hábil (lunes a sábado), con fondo inicial,
  algún retiro de efectivo y arqueo al cierre (casi siempre exacto, a veces
  con una diferencia chica, como pasa en la realidad);
- ventas de mostrador repartidas en el horario comercial, con productos de
  rotación alta más frecuentes, efectivo/tarjeta/transferencia y, a veces,
  cliente registrado o descuento;
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
    MovimientoInventarioModel,
    ProductoModel,
    VentaMostradorItemModel,
    VentaMostradorModel,
)

DIAS_DE_HISTORIAL = 42
FONDO_INICIAL = 300_000
MEDIOS_DE_PAGO = [("EFECTIVO", 55), ("TARJETA", 30), ("TRANSFERENCIA", 15)]


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
                    total_ventas_efectivo=0, total_ventas_tarjeta=0, total_ventas_transferencia=0,
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
        campo = {"EFECTIVO": "total_ventas_efectivo", "TARJETA": "total_ventas_tarjeta", "TRANSFERENCIA": "total_ventas_transferencia"}[metodo]
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
