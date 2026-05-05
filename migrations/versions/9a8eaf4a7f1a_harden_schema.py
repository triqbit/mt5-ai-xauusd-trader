"""harden schema

Revision ID: 9a8eaf4a7f1a
Revises: c1b7f28e5748
Create Date: 2026-05-05 06:24:31.553308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a8eaf4a7f1a'
down_revision: Union[str, None] = 'c1b7f28e5748'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # model_signals
    with op.batch_alter_table('model_signals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_model_signals_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_model_signals_is_deleted'), ['is_deleted'], unique=False)
        batch_op.create_index(batch_op.f('ix_model_signals_symbol'), ['symbol'], unique=False)
        batch_op.create_index(batch_op.f('ix_model_signals_timestamp'), ['timestamp'], unique=False)
        batch_op.create_check_constraint('check_signal_entry_price', 'entry_price > 0')
        batch_op.create_check_constraint('check_signal_lot_size', 'lot_size > 0')
        batch_op.create_check_constraint('check_signal_confidence', 'confidence >= 0 AND confidence <= 1')

    # trades
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_trades_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_is_deleted'), ['is_deleted'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_symbol'), ['symbol'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_status'), ['status'], unique=False)
        batch_op.create_check_constraint('check_trade_entry_price', 'entry_price > 0')
        batch_op.create_check_constraint('check_trade_lot_size', 'lot_size > 0')

    # risk_events
    with op.batch_alter_table('risk_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_risk_events_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_risk_events_is_deleted'), ['is_deleted'], unique=False)

    # performance_metrics
    with op.batch_alter_table('performance_metrics', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_performance_metrics_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_performance_metrics_is_deleted'), ['is_deleted'], unique=False)
        batch_op.create_index(batch_op.f('ix_performance_metrics_timestamp'), ['timestamp'], unique=False)


def downgrade() -> None:
    # performance_metrics
    with op.batch_alter_table('performance_metrics', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_performance_metrics_timestamp'))
        batch_op.drop_index(batch_op.f('ix_performance_metrics_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_performance_metrics_created_at'))
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')

    # risk_events
    with op.batch_alter_table('risk_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_risk_events_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_risk_events_created_at'))
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')

    # trades
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.drop_constraint('check_trade_lot_size', type_='check')
        batch_op.drop_constraint('check_trade_entry_price', type_='check')
        batch_op.drop_index(batch_op.f('ix_trades_status'))
        batch_op.drop_index(batch_op.f('ix_trades_symbol'))
        batch_op.drop_index(batch_op.f('ix_trades_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_trades_created_at'))
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')

    # model_signals
    with op.batch_alter_table('model_signals', schema=None) as batch_op:
        batch_op.drop_constraint('check_signal_confidence', type_='check')
        batch_op.drop_constraint('check_signal_lot_size', type_='check')
        batch_op.drop_constraint('check_signal_entry_price', type_='check')
        batch_op.drop_index(batch_op.f('ix_model_signals_timestamp'))
        batch_op.drop_index(batch_op.f('ix_model_signals_symbol'))
        batch_op.drop_index(batch_op.f('ix_model_signals_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_model_signals_created_at'))
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')
