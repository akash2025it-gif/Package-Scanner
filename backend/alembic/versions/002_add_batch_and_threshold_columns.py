"""Add batch intelligence and threshold automation columns

Revision ID: 002_add_batch_and_threshold_columns
Revises: 001_initial_schema
Create Date: 2026-09-06 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002_add_batch_and_threshold_columns'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add batch intelligence columns to scans table
    with op.batch_alter_table('scans') as batch_op:
        batch_op.add_column(sa.Column('batch_number', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('batch_number_extracted', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('batch_number_confidence', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('batch_number_source', sa.String(length=50), nullable=True, server_default='manual'))
        batch_op.add_column(sa.Column('batch_status', sa.String(length=50), nullable=True, server_default='normal'))
        batch_op.create_index('ix_scans_batch_number', ['batch_number'])

    # Add threshold automation and review columns to declarations table
    with op.batch_alter_table('declarations') as batch_op:
        batch_op.add_column(sa.Column('original_ai_status', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('original_ai_confidence', sa.Float(), nullable=True, server_default='0.0'))
        batch_op.add_column(sa.Column('violation_detection_rate', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('auto_confirm_threshold', sa.Float(), nullable=True, server_default='80.0'))
        batch_op.add_column(sa.Column('workflow_decision', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('decision_method', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('decision_reason', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('human_decision', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('reviewed_by', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('declarations') as batch_op:
        batch_op.drop_column('reviewed_at')
        batch_op.drop_column('reviewed_by')
        batch_op.drop_column('human_decision')
        batch_op.drop_column('decision_reason')
        batch_op.drop_column('decision_method')
        batch_op.drop_column('workflow_decision')
        batch_op.drop_column('auto_confirm_threshold')
        batch_op.drop_column('violation_detection_rate')
        batch_op.drop_column('original_ai_confidence')
        batch_op.drop_column('original_ai_status')

    with op.batch_alter_table('scans') as batch_op:
        batch_op.drop_index('ix_scans_batch_number')
        batch_op.drop_column('batch_status')
        batch_op.drop_column('batch_number_source')
        batch_op.drop_column('batch_number_confidence')
        batch_op.drop_column('batch_number_extracted')
        batch_op.drop_column('batch_number')
