"""Add broker orders

Revision ID: phase_9_3_broker_orders
Revises: phase_9_2_reconciliation
Create Date: 2026-09-30 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'phase_9_3_broker_orders'
down_revision = 'phase_9_2_reconciliation'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('broker_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('client_order_id', sa.String(), nullable=False),
        sa.Column('broker_order_id', sa.String(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('isin', sa.String(), nullable=True),
        sa.Column('exchange', sa.String(), nullable=False),
        sa.Column('side', sa.Enum('BUY', 'SELL', name='orderside'), nullable=False),
        sa.Column('quantity', sa.DECIMAL(), nullable=False),
        sa.Column('requested_quantity', sa.DECIMAL(), nullable=False),
        sa.Column('executed_quantity', sa.DECIMAL(), nullable=True),
        sa.Column('remaining_quantity', sa.DECIMAL(), nullable=False),
        sa.Column('price', sa.DECIMAL(), nullable=True),
        sa.Column('average_fill_price', sa.DECIMAL(), nullable=True),
        sa.Column('order_type', sa.String(), nullable=False),
        sa.Column('product', sa.String(), nullable=False),
        sa.Column('execution_intent', sa.Enum('DELIVERY_LONG_TERM', 'INTRADAY', 'MIS', 'MTF', 'MARGIN', 'LEVERAGE', 'SHORT', name='executionintent'), nullable=False),
        sa.Column('status', sa.Enum('CREATED', 'SUBMITTED', 'OPEN', 'PARTIALLY_FILLED', 'FILLED', 'CANCEL_REQUESTED', 'CANCELLED', 'REJECTED', 'FAILED', 'UNKNOWN', name='brokerorderstatus'), nullable=False),
        sa.Column('broker', sa.String(), nullable=False),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_code', sa.String(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('decision_id', sa.Integer(), nullable=True),
        sa.Column('risk_approval_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_broker_orders_client_order_id'), 'broker_orders', ['client_order_id'], unique=True)
    op.create_index(op.f('ix_broker_orders_broker_order_id'), 'broker_orders', ['broker_order_id'], unique=False)
    op.create_index(op.f('ix_broker_orders_id'), 'broker_orders', ['id'], unique=False)
    op.create_index(op.f('ix_broker_orders_portfolio_id'), 'broker_orders', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_broker_orders_user_id'), 'broker_orders', ['user_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_broker_orders_user_id'), table_name='broker_orders')
    op.drop_index(op.f('ix_broker_orders_portfolio_id'), table_name='broker_orders')
    op.drop_index(op.f('ix_broker_orders_id'), table_name='broker_orders')
    op.drop_index(op.f('ix_broker_orders_broker_order_id'), table_name='broker_orders')
    op.drop_index(op.f('ix_broker_orders_client_order_id'), table_name='broker_orders')
    op.drop_table('broker_orders')
