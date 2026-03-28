"""extend markets for ingest metadata"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260328_0002"
down_revision = "20260328_0001"
branch_labels = None
depends_on = None


def json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("markets")}
    indexes = {index["name"]: index for index in inspector.get_indexes("markets")}

    if "condition_id" not in columns:
        op.add_column("markets", sa.Column("condition_id", sa.String(length=128), nullable=True))
    if "outcomes" not in columns:
        op.add_column("markets", sa.Column("outcomes", json_type(), nullable=True))
    if "clob_token_ids" not in columns:
        op.add_column("markets", sa.Column("clob_token_ids", json_type(), nullable=True))
    if "source_payload" not in columns:
        op.add_column("markets", sa.Column("source_payload", json_type(), nullable=True))

    existing_index = indexes.get("ix_markets_condition_id")
    if existing_index and existing_index.get("unique"):
        op.drop_index("ix_markets_condition_id", table_name="markets")
        existing_index = None
    if existing_index is None:
        op.create_index("ix_markets_condition_id", "markets", ["condition_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("markets")}
    indexes = {index["name"] for index in inspector.get_indexes("markets")}

    if "ix_markets_condition_id" in indexes:
        op.drop_index("ix_markets_condition_id", table_name="markets")
    if "source_payload" in columns:
        op.drop_column("markets", "source_payload")
    if "clob_token_ids" in columns:
        op.drop_column("markets", "clob_token_ids")
    if "outcomes" in columns:
        op.drop_column("markets", "outcomes")
    if "condition_id" in columns:
        op.drop_column("markets", "condition_id")
