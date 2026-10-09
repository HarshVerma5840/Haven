"""Add identity mappings

Revision ID: acd6dd4e1b02
Revises: 
Create Date: 2026-10-08 19:11:25.940414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acd6dd4e1b02'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating identity database: creating identity_mappings table")
    op.create_table('identity_mappings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('employee_hash', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('github_username', sa.String(), nullable=True),
    sa.Column('hrms_employee_id', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_identity_mappings_email'), 'identity_mappings', ['email'], unique=True)
    op.create_index(op.f('ix_identity_mappings_employee_hash'), 'identity_mappings', ['employee_hash'], unique=True)
    op.create_index(op.f('ix_identity_mappings_github_username'), 'identity_mappings', ['github_username'], unique=True)
    op.create_index(op.f('ix_identity_mappings_hrms_employee_id'), 'identity_mappings', ['hrms_employee_id'], unique=True)
    op.create_index(op.f('ix_identity_mappings_id'), 'identity_mappings', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_identity_mappings_id'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_hrms_employee_id'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_github_username'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_employee_hash'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_email'), table_name='identity_mappings')
    op.drop_table('identity_mappings')
