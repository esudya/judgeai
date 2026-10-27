"""Add legal-source snapshots; existing case/practice tables remain untouched.

Backfill: none. Downgrade drops only the four new tables and their imported corpus;
export/back up this corpus before downgrade. No automatic production migration here.
"""
import sqlalchemy as sa
from alembic import op

revision = '0003_legal_library'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('legal_acts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(80), nullable=False, unique=True),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('number', sa.String(80)),
        sa.Column('adopted_on', sa.Date()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind IN ('constitution','code','federal_law','plenum',"
                           "'constitutional_court_decision')", name='ck_legal_acts_kind'))
    op.create_table('legal_editions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('act_id', sa.Integer(), sa.ForeignKey('legal_acts.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('label', sa.Text(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('source_sha256', sa.String(64), nullable=False),
        sa.Column('source_bytes', sa.LargeBinary(), nullable=False),
        sa.Column('full_text', sa.Text(), nullable=False),
        sa.Column('parser_version', sa.String(120), nullable=False),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verification_status', sa.String(20), server_default='unreviewed', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('act_id', 'source_sha256', name='uq_legal_edition_snapshot'),
        sa.CheckConstraint("verification_status IN ('unreviewed','verified','rejected')", name='ck_legal_edition_status'))
    op.create_index('ix_legal_editions_act_id', 'legal_editions', ['act_id'])
    op.create_table('legal_provisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('edition_id', sa.Integer(), sa.ForeignKey('legal_editions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('locator', sa.String(160), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('ordinal', sa.Integer(), nullable=False),
        sa.Column('start_page', sa.Integer()),
        sa.Column('end_page', sa.Integer()),
        sa.Column('effective_from', sa.Date()),
        sa.Column('effective_to', sa.Date()),
        sa.UniqueConstraint('edition_id', 'locator', name='uq_legal_provision_locator'),
        sa.UniqueConstraint('edition_id', 'ordinal', name='uq_legal_provision_order'),
        sa.CheckConstraint('ordinal >= 0', name='ck_legal_provision_order'),
        sa.CheckConstraint('effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from', name='ck_legal_provision_period'))
    op.create_index('ix_legal_provisions_edition_id', 'legal_provisions', ['edition_id'])
    op.create_table('legal_rule_references',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rule_key', sa.String(160), nullable=False),
        sa.Column('provision_id', sa.Integer(), sa.ForeignKey('legal_provisions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.UniqueConstraint('rule_key', 'provision_id', name='uq_legal_rule_reference'))
    op.create_index('ix_legal_rule_references_rule_key', 'legal_rule_references', ['rule_key'])
    op.create_index('ix_legal_rule_references_provision_id', 'legal_rule_references', ['provision_id'])


def downgrade():
    op.drop_table('legal_rule_references')
    op.drop_table('legal_provisions')
    op.drop_table('legal_editions')
    op.drop_table('legal_acts')
