"""Update identity models

Revision ID: a2482c99d090
Revises: acd6dd4e1b02
Create Date: 2026-10-08 19:27:42.200941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2482c99d090'
down_revision: Union[str, None] = 'acd6dd4e1b02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Migrating identity database: updating identity_mappings table")
    op.drop_index(op.f('ix_identity_mappings_email'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_github_username'), table_name='identity_mappings')
    op.drop_index(op.f('ix_identity_mappings_hrms_employee_id'), table_name='identity_mappings')


def downgrade() -> None:
    op.create_index(op.f('ix_identity_mappings_hrms_employee_id'), 'identity_mappings', ['hrms_employee_id'], unique=1)
    op.create_index(op.f('ix_identity_mappings_github_username'), 'identity_mappings', ['github_username'], unique=1)
    op.create_index(op.f('ix_identity_mappings_email'), 'identity_mappings', ['email'], unique=1)
