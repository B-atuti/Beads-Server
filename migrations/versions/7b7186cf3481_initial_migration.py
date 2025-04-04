"""Initial migration

Revision ID: 7b7186cf3481
Revises: 0d8d41de00e4
Create Date: 2025-03-25 18:04:16.612466

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7b7186cf3481'
down_revision = '0d8d41de00e4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.drop_column('price_per_unit')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('price_per_unit', sa.FLOAT(), nullable=False))

    # ### end Alembic commands ###
