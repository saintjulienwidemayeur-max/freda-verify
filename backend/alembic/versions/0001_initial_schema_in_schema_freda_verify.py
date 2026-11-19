"""initial schema in schema freda_verify

Revision ID: 0001
Revises: 
Create Date: 2026-11-19 23:49:04.411464
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('audit_logs',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=True),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('actor_api_key_id', sa.Uuid(), nullable=True),
    sa.Column('action', sa.String(length=64), nullable=False),
    sa.Column('target_type', sa.String(length=32), nullable=True),
    sa.Column('target_id', sa.String(length=64), nullable=True),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.Column('meta', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='freda_verify'
    )
    op.create_index('ix_audit_org_id', 'audit_logs', ['organization_id', 'id'], unique=False, schema='freda_verify')
    op.create_index(op.f('ix_freda_verify_audit_logs_action'), 'audit_logs', ['action'], unique=False, schema='freda_verify')
    op.create_table('organizations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('slug', sa.String(length=80), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='freda_verify'
    )
    op.create_index(op.f('ix_freda_verify_organizations_slug'), 'organizations', ['slug'], unique=True, schema='freda_verify')
    op.create_table('request_logs',
    sa.Column('id', sa.BigInteger().with_variant(sa.Integer(), 'sqlite'), autoincrement=True, nullable=False),
    sa.Column('request_id', sa.String(length=40), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=True),
    sa.Column('api_key_id', sa.Uuid(), nullable=True),
    sa.Column('method', sa.String(length=8), nullable=False),
    sa.Column('path', sa.String(length=200), nullable=False),
    sa.Column('status', sa.Integer(), nullable=False),
    sa.Column('latency_ms', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    schema='freda_verify'
    )
    op.create_index('ix_reqlog_org_time', 'request_logs', ['organization_id', 'created_at'], unique=False, schema='freda_verify')
    op.create_table('users',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_platform_admin', sa.Boolean(), nullable=False),
    sa.Column('failed_logins', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('mfa_enabled', sa.Boolean(), nullable=False),
    sa.Column('mfa_secret_enc', sa.String(length=255), nullable=True),
    sa.Column('mfa_last_step', sa.BigInteger(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    schema='freda_verify'
    )
    op.create_index(op.f('ix_freda_verify_users_email'), 'users', ['email'], unique=True, schema='freda_verify')
    op.create_table('api_keys',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('env', sa.String(length=8), nullable=False),
    sa.Column('prefix', sa.String(length=16), nullable=False),
    sa.Column('last4', sa.String(length=4), nullable=False),
    sa.Column('key_hash', sa.String(length=64), nullable=False),
    sa.Column('created_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['freda_verify.users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organization_id'], ['freda_verify.organizations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key_hash'),
    schema='freda_verify'
    )
    op.create_index(op.f('ix_freda_verify_api_keys_organization_id'), 'api_keys', ['organization_id'], unique=False, schema='freda_verify')
    op.create_table('memberships',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['organization_id'], ['freda_verify.organizations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['freda_verify.users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('organization_id', 'user_id', name='uq_membership'),
    schema='freda_verify'
    )
    op.create_index(op.f('ix_freda_verify_memberships_organization_id'), 'memberships', ['organization_id'], unique=False, schema='freda_verify')
    op.create_index(op.f('ix_freda_verify_memberships_user_id'), 'memberships', ['user_id'], unique=False, schema='freda_verify')
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['freda_verify.users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash'),
    schema='freda_verify'
    )
    op.create_index(op.f('ix_freda_verify_password_reset_tokens_user_id'), 'password_reset_tokens', ['user_id'], unique=False, schema='freda_verify')
    op.create_table('recovery_codes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['freda_verify.users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    schema='freda_verify'
    )
    op.create_index(op.f('ix_freda_verify_recovery_codes_user_id'), 'recovery_codes', ['user_id'], unique=False, schema='freda_verify')
    op.create_table('refresh_sessions',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('user_agent', sa.String(length=300), nullable=True),
    sa.Column('ip', sa.String(length=64), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['freda_verify.users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash'),
    schema='freda_verify'
    )
    op.create_index(op.f('ix_freda_verify_refresh_sessions_user_id'), 'refresh_sessions', ['user_id'], unique=False, schema='freda_verify')
    # ### end Alembic commands ###


    # Audit log is append-only: the database itself refuses UPDATE and DELETE (PostgreSQL).
    op.execute("""
        CREATE FUNCTION freda_verify.audit_logs_immutable() RETURNS trigger AS $$
        BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END; $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER audit_logs_no_change BEFORE UPDATE OR DELETE ON freda_verify.audit_logs FOR EACH ROW EXECUTE FUNCTION freda_verify.audit_logs_immutable()")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_change ON freda_verify.audit_logs")
    op.execute("DROP FUNCTION IF EXISTS freda_verify.audit_logs_immutable()")
    op.drop_index(op.f('ix_freda_verify_refresh_sessions_user_id'), table_name='refresh_sessions', schema='freda_verify')
    op.drop_table('refresh_sessions', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_recovery_codes_user_id'), table_name='recovery_codes', schema='freda_verify')
    op.drop_table('recovery_codes', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_password_reset_tokens_user_id'), table_name='password_reset_tokens', schema='freda_verify')
    op.drop_table('password_reset_tokens', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_memberships_user_id'), table_name='memberships', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_memberships_organization_id'), table_name='memberships', schema='freda_verify')
    op.drop_table('memberships', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_api_keys_organization_id'), table_name='api_keys', schema='freda_verify')
    op.drop_table('api_keys', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_users_email'), table_name='users', schema='freda_verify')
    op.drop_table('users', schema='freda_verify')
    op.drop_index('ix_reqlog_org_time', table_name='request_logs', schema='freda_verify')
    op.drop_table('request_logs', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_organizations_slug'), table_name='organizations', schema='freda_verify')
    op.drop_table('organizations', schema='freda_verify')
    op.drop_index(op.f('ix_freda_verify_audit_logs_action'), table_name='audit_logs', schema='freda_verify')
    op.drop_index('ix_audit_org_id', table_name='audit_logs', schema='freda_verify')
    op.drop_table('audit_logs', schema='freda_verify')
    # ### end Alembic commands ###
