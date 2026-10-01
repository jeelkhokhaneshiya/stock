"""Add reconciliation models

Revision ID: phase_9_2_reconciliation
Revises: 8a83c6e14a91
Create Date: 2026-09-30 16:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'phase_9_2_reconciliation'
down_revision = '8a83c6e14a91'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # We create the enums first if they don't exist, though typically handled via SQLAlchemy
    op.create_table('reconciliation_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('broker', sa.String(), nullable=False),
        sa.Column('status', sa.Enum('MATCHED', 'MISMATCH', 'BROKER_ONLY', 'INTERNAL_ONLY', 'ERROR', name='reconciliationstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reconciliation_runs_id'), 'reconciliation_runs', ['id'], unique=False)
    op.create_index(op.f('ix_reconciliation_runs_portfolio_id'), 'reconciliation_runs', ['portfolio_id'], unique=False)

    op.create_table('reconciliation_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('MATCHED', 'MISMATCH', 'BROKER_ONLY', 'INTERNAL_ONLY', 'ERROR', name='reconciliationstatus'), nullable=False),
        sa.Column('severity', sa.Enum('INFO', 'WARNING', 'CRITICAL', name='reconciliationseverity'), nullable=False),
        sa.Column('symbol', sa.String(), nullable=True),
        sa.Column('isin', sa.String(), nullable=True),
        sa.Column('exchange', sa.String(), nullable=True),
        sa.Column('broker_quantity', sa.DECIMAL(), nullable=True),
        sa.Column('internal_quantity', sa.DECIMAL(), nullable=True),
        sa.Column('quantity_difference', sa.DECIMAL(), nullable=True),
        sa.Column('broker_average_price', sa.DECIMAL(), nullable=True),
        sa.Column('internal_average_price', sa.DECIMAL(), nullable=True),
        sa.Column('price_difference', sa.DECIMAL(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['reconciliation_runs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reconciliation_items_id'), 'reconciliation_items', ['id'], unique=False)
    op.create_index(op.f('ix_reconciliation_items_run_id'), 'reconciliation_items', ['run_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_reconciliation_items_run_id'), table_name='reconciliation_items')
    op.drop_index(op.f('ix_reconciliation_items_id'), table_name='reconciliation_items')
    op.drop_table('reconciliation_items')
    op.drop_index(op.f('ix_reconciliation_runs_portfolio_id'), table_name='reconciliation_runs')
    op.drop_index(op.f('ix_reconciliation_runs_id'), table_name='reconciliation_runs')
    op.drop_table('reconciliation_runs')
