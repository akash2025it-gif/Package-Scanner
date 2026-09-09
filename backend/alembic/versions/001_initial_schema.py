"""Initial schema for PackCheck

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-09-02 23:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='inspector'),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Products table
    op.create_table(
        'products',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False, index=True),
        sa.Column('brand', sa.String(length=255), nullable=False, index=True),
        sa.Column('category', sa.String(length=100), nullable=False, index=True),
        sa.Column('manufacturer_name', sa.String(length=255), nullable=True),
        sa.Column('manufacturer_address', sa.Text(), nullable=True),
        sa.Column('country_of_origin', sa.String(length=100), nullable=True, server_default='India'),
        sa.Column('barcode', sa.String(length=100), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Scans table
    op.create_table(
        'scans',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('product_id', sa.String(length=36), sa.ForeignKey('products.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('inspector_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='physical_store'),
        sa.Column('source_url', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='processing', index=True),
        sa.Column('location_name', sa.String(length=255), nullable=True),
        sa.Column('gps_coordinates', sa.String(length=100), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Scan Images table
    op.create_table(
        'scan_images',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('scan_id', sa.String(length=36), sa.ForeignKey('scans.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('image_url', sa.Text(), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('image_type', sa.String(length=50), nullable=False, server_default='front'),
        sa.Column('width_px', sa.Integer(), nullable=True),
        sa.Column('height_px', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Declarations table
    op.create_table(
        'declarations',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('scan_id', sa.String(length=36), sa.ForeignKey('scans.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('field_type', sa.String(length=100), nullable=False, index=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('bounding_box', sa.JSON(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('font_size_mm', sa.Float(), nullable=True),
        sa.Column('is_present', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_compliant', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('rule_reference', sa.String(length=255), nullable=False),
        sa.Column('severity', sa.String(length=50), nullable=False, server_default='none'),
        sa.Column('reviewer_override', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('reviewer_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Compliance Reports table
    op.create_table(
        'compliance_reports',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('scan_id', sa.String(length=36), sa.ForeignKey('scans.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('generated_by', sa.String(length=36), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('overall_status', sa.String(length=50), nullable=False, server_default='non_compliant'),
        sa.Column('pdf_url', sa.String(length=512), nullable=True),
        sa.Column('docx_url', sa.String(length=512), nullable=True),
        sa.Column('summary_data', sa.JSON(), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # Audit Logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('action', sa.String(length=100), nullable=False, index=True),
        sa.Column('entity_type', sa.String(length=50), nullable=False, index=True),
        sa.Column('entity_id', sa.String(length=100), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('compliance_reports')
    op.drop_table('declarations')
    op.drop_table('scan_images')
    op.drop_table('scans')
    op.drop_table('products')
    op.drop_table('users')
