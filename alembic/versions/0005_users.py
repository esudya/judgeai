"""Add authentication; preserve existing cases under a disabled legacy account.

Back up before upgrade/downgrade. No account is provisioned with a usable password.
Downgrade removes ownership/authentication, not cases or analysis results.
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_users"
down_revision = "0004_criminal_article_sanctions"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "user_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_table(
        "auth_login_buckets",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("resets_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_auth_login_buckets_resets_at", "auth_login_buckets", ["resets_at"])
    op.execute(
        "INSERT INTO users (username, is_active, is_admin) VALUES ('__legacy_locked__', false, false)"
    )
    op.add_column("messages", sa.Column("request_message_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_messages_request_message_id",
        "messages",
        "messages",
        ["request_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_messages_request_message_id", "messages", ["request_message_id"], unique=True
    )
    op.add_column("chats", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_chats_owner_id_users", "chats", "users", ["owner_id"], ["id"], ondelete="RESTRICT"
    )
    op.create_index("ix_chats_owner_id", "chats", ["owner_id"])
    op.execute(
        "UPDATE chats SET owner_id = (SELECT id FROM users WHERE username = '__legacy_locked__') WHERE owner_id IS NULL"
    )


def downgrade():
    op.drop_index("ix_messages_request_message_id", table_name="messages")
    op.drop_constraint("fk_messages_request_message_id", "messages", type_="foreignkey")
    op.drop_column("messages", "request_message_id")
    op.drop_index("ix_chats_owner_id", table_name="chats")
    op.drop_constraint("fk_chats_owner_id_users", "chats", type_="foreignkey")
    op.drop_column("chats", "owner_id")
    op.drop_table("auth_login_buckets")
    op.drop_table("user_sessions")
    op.drop_table("users")
