"""Formato de cantidades para los mensajes al usuario, como se escriben en
Paraguay: punto de miles y coma decimal, sin ceros de más ("1.800", "2,5")."""
from decimal import Decimal, InvalidOperation


def formato_cantidad(valor) -> str:
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        return str(valor)
    numero = numero.quantize(Decimal("0.001")).normalize()
    signo = "-" if numero < 0 else ""
    entero, _, decimales = f"{abs(numero):f}".partition(".")
    miles = f"{int(entero):,}".replace(",", ".")
    return f"{signo}{miles},{decimales}" if decimales else f"{signo}{miles}"
