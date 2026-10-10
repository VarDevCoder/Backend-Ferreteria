"""Expresiones SQL para fechas en la hora de la empresa (ver app/core/tiempo.py).

Las columnas `created_at` son `timestamp` sin zona con la hora UTC:
`timezone('UTC', col)` las marca como UTC y `timezone(<zona>, ...)` las pasa a
la hora local de la ferretería.
"""
from sqlalchemy import func, literal_column

from app.core.tiempo import zona


def _texto(valor: str):
    # Literal en el SQL (no parámetro): así la misma expresión puede ir en el
    # SELECT y en el GROUP BY. La zona viene de la configuración y ZoneInfo ya
    # la validó; igual se escapan las comillas.
    return literal_column("'" + valor.replace("'", "''") + "'")


def en_hora_local(columna):
    return func.timezone(_texto(zona().key), func.timezone(_texto("UTC"), columna))


def fecha_local(columna):
    """Fecha local (date) de un momento guardado en UTC."""
    return func.date(en_hora_local(columna))


def anio_local(columna):
    return func.extract("year", en_hora_local(columna))


def ahora_local_sql():
    """`now()` (con zona) pasado a la hora de la empresa."""
    return func.timezone(_texto(zona().key), func.now())


def hoy_sql():
    """La fecha de hoy en la hora de la empresa, calculada por la base."""
    return func.date(ahora_local_sql())


def anio_actual_sql():
    return func.extract("year", ahora_local_sql())
