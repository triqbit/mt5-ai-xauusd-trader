"""Harden schema and add indexes

Revision ID: 9a8eaf4a7f1a
Revises: c1b7f28e5748
Create Date: 2026-05-04 06:30:27.193286

"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a8eaf4a7f1a'
down_revision: Union[str, None] = 'c1b7f28e5748'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for SQLite compatibility
    with op.batch_alter_table('model_signals') as batch_op:
        batch_op.add_column(sa.Column('volatility', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.alter_column('timestamp',
                   existing_type=sa.DATETIME(),
                   nullable=False,
                   server_default=sa.func.current_timestamp())
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=False,
                   server_default=sa.text('0'))
        batch_op.create_index(batch_op.f('ix_model_signals_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_model_signals_is_deleted'), ['is_deleted'], unique=False)
        batch_op.create_index(batch_op.f('ix_model_signals_symbol'), ['symbol'], unique=False)
        batch_op.create_index('ix_model_signals_symbol_created_at', ['symbol', 'created_at'], unique=False)
        batch_op.create_check_constraint('check_signal_entry_price_positive', 'entry_price > 0')
        batch_op.create_check_constraint('check_signal_lot_size_positive', 'lot_size > 0')
        batch_op.create_check_constraint('check_signal_confidence_range', 'confidence >= 0 AND confidence <= 1')

    with op.batch_alter_table('performance_metrics') as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.alter_column('timestamp',
                   existing_type=sa.DATETIME(),
                   nullable=False,
                   server_default=sa.func.current_timestamp())
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=False,
                   server_default=sa.text('0'))
        batch_op.create_index(batch_op.f('ix_performance_metrics_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_performance_metrics_is_deleted'), ['is_deleted'], unique=False)

    with op.batch_alter_table('risk_events') as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=False,
                   server_default=sa.text('0'))
        batch_op.create_index(batch_op.f('ix_risk_events_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_risk_events_is_deleted'), ['is_deleted'], unique=False)

    with op.batch_alter_table('trades') as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('updated_by', sa.String(length=100), nullable=True))
        batch_op.alter_column('pnl',
                   existing_type=sa.FLOAT(),
                   nullable=False,
                   server_default=sa.text('0.0'))
        batch_op.alter_column('status',
                   existing_type=sa.VARCHAR(length=20),
                   nullable=False,
                   server_default='OPEN')
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=False,
                   server_default=sa.text('0'))
        batch_op.create_index(batch_op.f('ix_trades_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_is_deleted'), ['is_deleted'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_symbol'), ['symbol'], unique=False)
        batch_op.create_index('ix_trades_symbol_status_is_deleted', ['symbol', 'status', 'is_deleted'], unique=False)
        batch_op.create_check_constraint('check_trade_entry_price_positive', 'entry_price > 0')
        batch_op.create_check_constraint('check_trade_lot_size_positive', 'lot_size > 0')


def downgrade() -> None:
    with op.batch_alter_table('trades') as batch_op:
        batch_op.drop_constraint('check_trade_lot_size_positive', type_='check')
        batch_op.drop_constraint('check_trade_entry_price_positive', type_='check')
        batch_op.drop_index('ix_trades_symbol_status_is_deleted')
        batch_op.drop_index(batch_op.f('ix_trades_symbol'))
        batch_op.drop_index(batch_op.f('ix_trades_status'))
        batch_op.drop_index(batch_op.f('ix_trades_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_trades_created_at'))
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=None)
        batch_op.alter_column('status',
                   existing_type=sa.VARCHAR(length=20),
                   nullable=True,
                   server_default=None)
        batch_op.alter_column('pnl',
                   existing_type=sa.FLOAT(),
                   nullable=True,
                   server_default=None)
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')

    with op.batch_alter_table('risk_events') as batch_op:
        batch_op.drop_index(batch_op.f('ix_risk_events_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_risk_events_created_at'))
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=None)
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')

    with op.batch_alter_table('performance_metrics') as batch_op:
        batch_op.drop_index(batch_op.f('ix_performance_metrics_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_performance_metrics_created_at'))
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=None)
        batch_op.alter_column('timestamp',
                   existing_type=sa.DATETIME(),
                   nullable=True,
                   server_default=None)
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')

    with op.batch_alter_table('model_signals') as batch_op:
        batch_op.drop_constraint('check_signal_confidence_range', type_='check')
        batch_op.drop_constraint('check_signal_lot_size_positive', type_='check')
        batch_op.drop_constraint('check_signal_entry_price_positive', type_='check')
        batch_op.drop_index('ix_model_signals_symbol_created_at')
        batch_op.drop_index(batch_op.f('ix_model_signals_symbol'))
        batch_op.drop_index(batch_op.f('ix_model_signals_is_deleted'))
        batch_op.drop_index(batch_op.f('ix_model_signals_created_at'))
        batch_op.alter_column('is_deleted',
                   existing_type=sa.BOOLEAN(),
                   nullable=True,
                   server_default=None)
        batch_op.alter_column('timestamp',
                   existing_type=sa.DATETIME(),
                   nullable=True,
                   server_default=None)
        batch_op.drop_column('updated_by')
        batch_op.drop_column('created_by')
        batch_op.drop_column('volatility')
