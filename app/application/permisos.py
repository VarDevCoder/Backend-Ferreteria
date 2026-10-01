"""Qué rol puede modificar qué módulo.

Regla general: todo el personal puede *consultar* todos los módulos (un
vendedor necesita ver el stock, el depósito necesita ver los pedidos). Lo
que se restringe por rol es *crear, modificar o cambiar de estado*
documentos. Usuarios y configuración de la empresa son solo del admin.

Este mapa también se expone al frontend (`GET /auth/me`) para que oculte
los botones que el usuario no puede usar; la validación real es la del
backend.
"""
from enum import StrEnum

from app.domain.enums import RolUsuario

A = RolUsuario.ADMIN
E = RolUsuario.ENCARGADO
V = RolUsuario.VENDEDOR
D = RolUsuario.DEPOSITO


class Modulo(StrEnum):
    CAJA = "caja"
    PEDIDOS = "pedidos"
    CLIENTES = "clientes"
    PROVEEDORES = "proveedores"
    CATALOGO = "catalogo"
    COTIZACIONES = "cotizaciones"
    ORDENES_COMPRA = "ordenes_compra"
    ORDENES_ENVIO = "ordenes_envio"
    INVENTARIO = "inventario"
    REPORTES = "reportes"
    USUARIOS = "usuarios"
    EMPRESA = "empresa"


PUEDE_MODIFICAR: dict[Modulo, frozenset[RolUsuario]] = {
    Modulo.CAJA: frozenset({A, E, V}),
    Modulo.PEDIDOS: frozenset({A, E, V}),
    Modulo.CLIENTES: frozenset({A, E, V}),
    Modulo.PROVEEDORES: frozenset({A, E}),
    Modulo.CATALOGO: frozenset({A, E, D}),
    Modulo.COTIZACIONES: frozenset({A, E}),
    Modulo.ORDENES_COMPRA: frozenset({A, E, D}),
    Modulo.ORDENES_ENVIO: frozenset({A, E, D}),
    Modulo.INVENTARIO: frozenset({A, E, D}),
    Modulo.REPORTES: frozenset({A, E}),
    Modulo.USUARIOS: frozenset({A}),
    Modulo.EMPRESA: frozenset({A}),
}

# Módulos que ni siquiera se pueden consultar sin permiso (datos sensibles:
# ventas y márgenes, cuentas del personal).
SOLO_CON_PERMISO_PARA_LEER = frozenset({Modulo.REPORTES, Modulo.USUARIOS})


# Quién puede vender a un precio distinto del de lista (el resto vende al
# precio del catálogo y, como mucho, aplica el descuento de la venta).
PUEDEN_CAMBIAR_PRECIO_DE_VENTA = frozenset({A, E})


def puede_cambiar_precio_de_venta(rol: RolUsuario) -> bool:
    return rol in PUEDEN_CAMBIAR_PRECIO_DE_VENTA


def puede_modificar(rol: RolUsuario, modulo: Modulo) -> bool:
    return rol in PUEDE_MODIFICAR[modulo]


def puede_leer(rol: RolUsuario, modulo: Modulo) -> bool:
    if modulo in SOLO_CON_PERMISO_PARA_LEER:
        return puede_modificar(rol, modulo)
    return rol in RolUsuario.internos()


def modulos_modificables(rol: RolUsuario) -> list[str]:
    """Permisos que se informan al frontend: módulos modificables más
    permisos puntuales (ej. `precios_venta`)."""
    permisos = [m.value for m in Modulo if puede_modificar(rol, m)]
    if puede_cambiar_precio_de_venta(rol):
        permisos.append("precios_venta")
    return permisos
