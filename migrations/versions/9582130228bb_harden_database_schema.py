"""harden database schema

Revision ID: 9582130228bb
Revises: c1b7f28e5748
Create Date: 2026-05-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9582130228bb'
down_revision: Union[str, None] = 'c1b7f28e5748'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add missing indexes for performance on columns not already indexed in initial migration
    # Note: 'symbol' and 'is_deleted' were NOT indexed in c1b7f28e5748 for most tables
    # except 'trades.ticket' and 'trades.symbol'.

    op.create_index(op.f('ix_model_signals_created_at'), 'model_signals', ['created_at'], unique=False)
    op.create_index(op.f('ix_model_signals_is_deleted'), 'model_signals', ['is_deleted'], unique=False)
    # symbol was not indexed in initial migration for model_signals
    op.create_index(op.f('ix_model_signals_symbol'), 'model_signals', ['symbol'], unique=False)

    op.create_index(op.f('ix_trades_created_at'), 'trades', ['created_at'], unique=False)
    op.create_index(op.f('ix_trades_is_deleted'), 'trades', ['is_deleted'], unique=False)
    # trades.symbol WAS indexed in initial migration, so we skip it to avoid duplicates
    op.create_index(op.f('ix_trades_status'), 'trades', ['status'], unique=False)

    op.create_index(op.f('ix_risk_events_created_at'), 'risk_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_risk_events_is_deleted'), 'risk_events', ['is_deleted'], unique=False)

    op.create_index(op.f('ix_performance_metrics_created_at'), 'performance_metrics', ['created_at'], unique=False)
    op.create_index(op.f('ix_performance_metrics_is_deleted'), 'performance_metrics', ['is_deleted'], unique=False)

    # 2. Harden is_deleted column and add CheckConstraints
    # We use batch_alter_table to support SQLite safely

    with op.batch_alter_table('model_signals') as batch_op:
        batch_op.alter_column('is_deleted', nullable=False, server_default=sa.text('0'))
        batch_op.create_check_constraint('check_signal_entry_price_positive', 'entry_price > 0')
        batch_op.create_check_constraint('check_signal_direction_valid', 'direction IN (-1, 0, 1)')
        batch_op.create_check_constraint('check_signal_lot_size_positive', 'lot_size IS NULL OR lot_size > 0')

    with op.batch_alter_table('trades') as batch_op:
        batch_op.alter_column('is_deleted', nullable=False, server_default=sa.text('0'))
        batch_op.create_check_constraint('check_trade_entry_price_positive', 'entry_price > 0')
        batch_op.create_check_constraint('check_trade_direction_valid', 'direction IN (-1, 0, 1)')
        batch_op.create_check_constraint('check_trade_lot_size_positive', 'lot_size > 0')

    with op.batch_alter_table('risk_events') as batch_op:
        batch_op.alter_column('is_deleted', nullable=False, server_default=sa.text('0'))

    with op.batch_alter_table('performance_metrics') as batch_op:
        batch_op.alter_column('is_deleted', nullable=False, server_default=sa.text('0'))


def downgrade() -> None:
    # 1. Revert hardening of is_deleted and remove CheckConstraints
    with op.batch_alter_table('performance_metrics') as batch_op:
        batch_op.alter_column('is_deleted', nullable=True, server_default=None)

    with op.batch_alter_table('risk_events') as batch_op:
        batch_op.alter_column('is_deleted', nullable=True, server_default=None)

    with op.batch_alter_table('trades') as batch_op:
        batch_op.drop_constraint('check_trade_lot_size_positive', type_='check')
        batch_op.drop_constraint('check_trade_direction_valid', type_='check')
        batch_op.drop_constraint('check_trade_entry_price_positive', type_='check')
        batch_op.alter_column('is_deleted', nullable=True, server_default=None)

    with op.batch_alter_table('model_signals') as batch_op:
        batch_op.drop_constraint('check_signal_lot_size_positive', type_='check')
        batch_op.drop_constraint('check_signal_direction_valid', type_='check')
        batch_op.drop_constraint('check_signal_entry_price_positive', type_='check')
        batch_op.alter_column('is_deleted', nullable=True, server_default=None)

    # 2. Remove indexes
    op.drop_index(op.f('ix_performance_metrics_is_deleted'), table_name='performance_metrics')
    op.drop_index(op.f('ix_performance_metrics_created_at'), table_name='performance_metrics')

    op.drop_index(op.f('ix_risk_events_is_deleted'), table_name='risk_events')
    op.drop_index(op.f('ix_risk_events_created_at'), table_name='risk_events')

    op.drop_index(op.f('ix_trades_status'), table_name='trades')
    op.drop_index(op.f('ix_trades_is_deleted'), table_name='trades')
    op.drop_index(op.f('ix_trades_created_at'), table_name='trades')

    op.drop_index(op.f('ix_model_signals_symbol'), table_name='model_signals')
    op.drop_index(op.f('ix_model_signals_is_deleted'), table_name='model_signals')
    op.drop_index(op.f('ix_model_signals_created_at'), table_name='model_signals')
