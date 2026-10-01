"""numeración de pedidos PED-AAAA-NNNN

Revision ID: 9e3f4a5b6c7d
Revises: 8d2e3f4a5b6c
Create Date: 2026-10-02 18:00:00.000000

Los pedidos de cliente se numeraban "Solicitud #N", que se confundía con
las solicitudes de presupuesto a proveedores. Pasan al mismo formato que
el resto de los documentos (OC-, ENV-, VTA-): PED-<año>-<correlativo>.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9e3f4a5b6c7d'
down_revision: Union[str, Sequence[str], None] = '8d2e3f4a5b6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE pedidos_cliente p
        SET numero = 'PED-' || n.anio || '-' || LPAD(n.correlativo::text, 4, '0')
        FROM (
            SELECT id,
                   EXTRACT(YEAR FROM created_at)::int AS anio,
                   ROW_NUMBER() OVER (PARTITION BY EXTRACT(YEAR FROM created_at) ORDER BY id) AS correlativo
            FROM pedidos_cliente
        ) n
        WHERE p.id = n.id
    """)


def downgrade() -> None:
    op.execute("UPDATE pedidos_cliente SET numero = 'Solicitud #' || id")
