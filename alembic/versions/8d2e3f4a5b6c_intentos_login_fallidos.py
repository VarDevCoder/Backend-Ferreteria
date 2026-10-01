"""intentos de login fallidos

Revision ID: 8d2e3f4a5b6c
Revises: 7c1d2e3f4a5b
Create Date: 2026-10-02 12:00:00.000000

Guarda las contraseñas incorrectas recientes en la base para que el
bloqueo por fuerza bruta funcione en Vercel (serverless: no hay memoria
compartida entre instancias).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8d2e3f4a5b6c'
down_revision: Union[str, Sequence[str], None] = '7c1d2e3f4a5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'intentos_login_fallidos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_intentos_login_fallidos_email'), 'intentos_login_fallidos', ['email'])
    op.create_index(op.f('ix_intentos_login_fallidos_created_at'), 'intentos_login_fallidos', ['created_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_intentos_login_fallidos_created_at'), table_name='intentos_login_fallidos')
    op.drop_index(op.f('ix_intentos_login_fallidos_email'), table_name='intentos_login_fallidos')
    op.drop_table('intentos_login_fallidos')
