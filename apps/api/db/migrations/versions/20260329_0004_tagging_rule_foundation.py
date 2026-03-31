"""add tagging rule foundation tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260329_0004"
down_revision = "20260329_0003"
branch_labels = None
depends_on = None


def json_type():
    return sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def uuid_type():
    return sa.UUID().with_variant(postgresql.UUID(as_uuid=True), "postgresql")


def upgrade() -> None:
    op.create_table(
        "tag_dictionary_entries",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("tag_code", sa.String(length=64), nullable=False),
        sa.Column("tag_name", sa.String(length=128), nullable=False),
        sa.Column("tag_type", sa.String(length=32), nullable=False),
        sa.Column("dimension", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("aliases", json_type(), nullable=True),
        sa.Column("tag_metadata", json_type(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tag_dictionary_entries"),
        sa.UniqueConstraint("tag_code", name="uq_tag_dictionary_entries_tag_code"),
    )
    op.create_index("ix_tag_dictionary_entries_tag_code", "tag_dictionary_entries", ["tag_code"], unique=False)
    op.create_index("ix_tag_dictionary_entries_tag_type", "tag_dictionary_entries", ["tag_type"], unique=False)
    op.create_index("ix_tag_dictionary_entries_dimension", "tag_dictionary_entries", ["dimension"], unique=False)
    op.create_index(
        "ix_tag_dictionary_entries_tag_type_dimension",
        "tag_dictionary_entries",
        ["tag_type", "dimension"],
        unique=False,
    )

    op.create_table(
        "tag_rule_versions",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("version_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("release_kind", sa.String(length=32), nullable=False, server_default="standard"),
        sa.Column("base_version_id", uuid_type(), nullable=True),
        sa.Column("supersedes_version_id", uuid_type(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("impact_summary", sa.Text(), nullable=True),
        sa.Column("rollback_plan", sa.Text(), nullable=True),
        sa.Column("version_notes", sa.Text(), nullable=True),
        sa.Column("dictionary_snapshot", json_type(), nullable=False),
        sa.Column("config_payload", json_type(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("activated_by", sa.String(length=128), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["base_version_id"],
            ["tag_rule_versions.id"],
            name="fk_tag_rule_versions_base_version_id_tag_rule_versions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["tag_rule_versions.id"],
            name="fk_tag_rule_versions_supersedes_version_id_tag_rule_versions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tag_rule_versions"),
        sa.UniqueConstraint("version_code", name="uq_tag_rule_versions_version_code"),
    )
    op.create_index("ix_tag_rule_versions_version_code", "tag_rule_versions", ["version_code"], unique=False)
    op.create_index("ix_tag_rule_versions_status", "tag_rule_versions", ["status"], unique=False)
    op.create_index("ix_tag_rule_versions_release_kind", "tag_rule_versions", ["release_kind"], unique=False)
    op.create_index("ix_tag_rule_versions_base_version_id", "tag_rule_versions", ["base_version_id"], unique=False)
    op.create_index(
        "ix_tag_rule_versions_supersedes_version_id",
        "tag_rule_versions",
        ["supersedes_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_tag_rule_versions_status_created_at",
        "tag_rule_versions",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "tag_rules",
        sa.Column("id", uuid_type(), nullable=False),
        sa.Column("rule_version_id", uuid_type(), nullable=False),
        sa.Column("rule_code", sa.String(length=64), nullable=False),
        sa.Column("rule_name", sa.String(length=128), nullable=False),
        sa.Column("rule_kind", sa.String(length=32), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("target_tag_code", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("match_scope", json_type(), nullable=False),
        sa.Column("match_operator", sa.String(length=32), nullable=False),
        sa.Column("match_payload", json_type(), nullable=False),
        sa.Column("effect_payload", json_type(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rule_version_id"],
            ["tag_rule_versions.id"],
            name="fk_tag_rules_rule_version_id_tag_rule_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tag_rules"),
        sa.UniqueConstraint("rule_version_id", "rule_code", name="uq_tag_rules_rule_version_id_rule_code"),
    )
    op.create_index("ix_tag_rules_rule_kind", "tag_rules", ["rule_kind"], unique=False)
    op.create_index("ix_tag_rules_action_type", "tag_rules", ["action_type"], unique=False)
    op.create_index("ix_tag_rules_target_tag_code", "tag_rules", ["target_tag_code"], unique=False)
    op.create_index(
        "ix_tag_rules_rule_version_id_priority",
        "tag_rules",
        ["rule_version_id", "priority"],
        unique=False,
    )
    op.create_index(
        "ix_tag_rules_target_tag_code_enabled",
        "tag_rules",
        ["target_tag_code", "enabled"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tag_rules_target_tag_code_enabled", table_name="tag_rules")
    op.drop_index("ix_tag_rules_rule_version_id_priority", table_name="tag_rules")
    op.drop_index("ix_tag_rules_target_tag_code", table_name="tag_rules")
    op.drop_index("ix_tag_rules_action_type", table_name="tag_rules")
    op.drop_index("ix_tag_rules_rule_kind", table_name="tag_rules")
    op.drop_table("tag_rules")

    op.drop_index("ix_tag_rule_versions_status_created_at", table_name="tag_rule_versions")
    op.drop_index("ix_tag_rule_versions_supersedes_version_id", table_name="tag_rule_versions")
    op.drop_index("ix_tag_rule_versions_base_version_id", table_name="tag_rule_versions")
    op.drop_index("ix_tag_rule_versions_release_kind", table_name="tag_rule_versions")
    op.drop_index("ix_tag_rule_versions_status", table_name="tag_rule_versions")
    op.drop_index("ix_tag_rule_versions_version_code", table_name="tag_rule_versions")
    op.drop_table("tag_rule_versions")

    op.drop_index("ix_tag_dictionary_entries_tag_type_dimension", table_name="tag_dictionary_entries")
    op.drop_index("ix_tag_dictionary_entries_dimension", table_name="tag_dictionary_entries")
    op.drop_index("ix_tag_dictionary_entries_tag_type", table_name="tag_dictionary_entries")
    op.drop_index("ix_tag_dictionary_entries_tag_code", table_name="tag_dictionary_entries")
    op.drop_table("tag_dictionary_entries")
