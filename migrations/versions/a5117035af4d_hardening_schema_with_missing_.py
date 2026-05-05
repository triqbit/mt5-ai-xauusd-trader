"""Hardening schema with missing volatility column and indices

Revision ID: a5117035af4d
Revises: c1b7f28e5748
Create Date: 2026-05-05 07:28:38.635057

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5117035af4d'
down_revision: Union[str, None] = 'c1b7f28e5748'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('model_signals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('volatility', sa.Float(), nullable=True))
        batch_op.create_index(batch_op.f('ix_model_signals_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_model_signals_is_deleted'), ['is_deleted'], unique=False)
        batch_op.create_index(batch_op.f('ix_model_signals_symbol'), ['symbol'], unique=False)

    with op.batch_alter_table('performance_metrics', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_performance_metrics_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_performance_metrics_is_deleted'), ['is_deleted'], unique=False)

    with op.batch_alter_table('risk_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_risk_events_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_risk_events_is_deleted'), ['is_deleted'], unique=False)

    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_trades_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_is_deleted'), ['is_deleted'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_symbol'), ['symbol'], unique=False)


def downgrade() -> None:
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_trades_symbol'))
        batch_op.drop_index(batch_op.f('ix_trades_status'))
        batch_op.drop_index(batch_op.f('ix_trades_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_trades_created_at'))

    with op.batch_alter_table('risk_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_risk_events_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_risk_events_created_at'))

    with op.batch_alter_table('performance_metrics', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_performance_metrics_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_performance_metrics_created_at'))

    with op.batch_alter_table('model_signals', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_model_signals_symbol'))
        batch_op.drop_index(batch_op.f('ix_model_signals_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_model_signals_created_at'))
        batch_op.drop_column('volatility')
