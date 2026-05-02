"""add_integrity_constraints_and_indexes

Revision ID: d17e71df27e8
Revises: c1b7f28e5748
Create Date: 2026-05-02 06:35:45.699962

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd17e71df27e8'
down_revision: Union[str, None] = 'c1b7f28e5748'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure no NULLs exist for is_deleted before making it non-nullable
    op.execute("UPDATE model_signals SET is_deleted = 0 WHERE is_deleted IS NULL")
    op.execute("UPDATE trades SET is_deleted = 0 WHERE is_deleted IS NULL")
    op.execute("UPDATE risk_events SET is_deleted = 0 WHERE is_deleted IS NULL")
    op.execute("UPDATE performance_metrics SET is_deleted = 0 WHERE is_deleted IS NULL")

    # 1. model_signals table
    with op.batch_alter_table('model_signals', schema=None) as batch_op:
        batch_op.create_index('ix_model_signals_symbol', ['symbol'], unique=False)
        batch_op.create_index('ix_model_signals_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_model_signals_is_deleted', ['is_deleted'], unique=False)
        batch_op.create_check_constraint('ck_model_signals_direction', 'direction IN (-1, 0, 1)')
        batch_op.create_check_constraint('ck_model_signals_entry_price', 'entry_price > 0')
        batch_op.create_check_constraint('ck_model_signals_lot_size', 'lot_size > 0')
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=False, server_default=sa.text('0'))

    # 2. trades table
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.create_index('ix_trades_symbol', ['symbol'], unique=False)
        batch_op.create_index('ix_trades_status', ['status'], unique=False)
        batch_op.create_index('ix_trades_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_trades_is_deleted', ['is_deleted'], unique=False)
        batch_op.create_check_constraint('ck_trades_direction', 'direction IN (-1, 0, 1)')
        batch_op.create_check_constraint('ck_trades_entry_price', 'entry_price > 0')
        batch_op.create_check_constraint('ck_trades_lot_size', 'lot_size > 0')
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=False, server_default=sa.text('0'))

    # 3. risk_events table
    with op.batch_alter_table('risk_events', schema=None) as batch_op:
        batch_op.create_index('ix_risk_events_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_risk_events_is_deleted', ['is_deleted'], unique=False)
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=False, server_default=sa.text('0'))

    # 4. performance_metrics table
    with op.batch_alter_table('performance_metrics', schema=None) as batch_op:
        batch_op.create_index('ix_performance_metrics_created_at', ['created_at'], unique=False)
        batch_op.create_index('ix_performance_metrics_is_deleted', ['is_deleted'], unique=False)
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=False, server_default=sa.text('0'))


def downgrade() -> None:
    # 4. performance_metrics table
    with op.batch_alter_table('performance_metrics', schema=None) as batch_op:
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=True)
        batch_op.drop_index('ix_performance_metrics_is_deleted')
        batch_op.drop_index('ix_performance_metrics_created_at')

    # 3. risk_events table
    with op.batch_alter_table('risk_events', schema=None) as batch_op:
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=True)
        batch_op.drop_index('ix_risk_events_is_deleted')
        batch_op.drop_index('ix_risk_events_created_at')

    # 2. trades table
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=True)
        batch_op.drop_constraint('ck_trades_lot_size', type_='check')
        batch_op.drop_constraint('ck_trades_entry_price', type_='check')
        batch_op.drop_constraint('ck_trades_direction', type_='check')
        batch_op.drop_index('ix_trades_is_deleted')
        batch_op.drop_index('ix_trades_created_at')
        batch_op.drop_index('ix_trades_status')
        batch_op.drop_index('ix_trades_symbol')

    # 1. model_signals table
    with op.batch_alter_table('model_signals', schema=None) as batch_op:
        batch_op.alter_column('is_deleted', existing_type=sa.Boolean(), nullable=True)
        batch_op.drop_constraint('ck_model_signals_lot_size', type_='check')
        batch_op.drop_constraint('ck_model_signals_entry_price', type_='check')
        batch_op.drop_constraint('ck_model_signals_direction', type_='check')
        batch_op.drop_index('ix_model_signals_is_deleted')
        batch_op.drop_index('ix_model_signals_created_at')
        batch_op.drop_index('ix_model_signals_symbol')
