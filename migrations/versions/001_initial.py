"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(64), nullable=False),
        sa.Column('email', sa.String(128), nullable=True),
        sa.Column('hashed_password', sa.String(256), nullable=False),
        sa.Column('role', sa.Enum('super_admin', 'admin', 'support', 'read_only', 'user', name='userrole'), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('theme', sa.String(16), nullable=False, server_default='dark'),
        sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('two_factor_secret', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    op.create_table(
        'vps_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('cpu', sa.Integer(), nullable=False),
        sa.Column('ram', sa.Integer(), nullable=False),
        sa.Column('storage', sa.Integer(), nullable=False),
        sa.Column('bandwidth', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ipv4_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('ipv6_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('price', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'operating_systems',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('version', sa.String(32), nullable=False),
        sa.Column('docker_image', sa.String(128), nullable=False),
        sa.Column('display_name', sa.String(128), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_os_name_version'),
    )

    op.create_table(
        'hosts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('endpoint', sa.String(256), nullable=False),
        sa.Column('provider_type', sa.String(32), nullable=False, server_default='docker'),
        sa.Column('credentials', sa.JSON(), nullable=True),
        sa.Column('cpu_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ram_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('cpu_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ram_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('storage_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('vps_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    op.create_table(
        'settings',
        sa.Column('key', sa.String(64), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('key'),
    )

    op.create_table(
        'vps_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vps_id', sa.String(32), nullable=False),
        sa.Column('provider_id', sa.String(128), nullable=True),
        sa.Column('token', sa.String(64), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('os_id', sa.Integer(), nullable=True),
        sa.Column('cpu', sa.Integer(), nullable=False),
        sa.Column('ram', sa.Integer(), nullable=False),
        sa.Column('storage', sa.Integer(), nullable=False),
        sa.Column('bandwidth_limit', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hostname', sa.String(64), nullable=False),
        sa.Column('root_password', sa.String(128), nullable=True),
        sa.Column('ssh_port', sa.Integer(), nullable=False, server_default='22'),
        sa.Column('additional_ports', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('ipv4', sa.String(45), nullable=True),
        sa.Column('ipv6', sa.String(45), nullable=True),
        sa.Column('status', sa.Enum('creating', 'running', 'stopped', 'starting', 'stopping', 'restarting', 'rebuilding', 'deleting', 'error', 'suspended', 'expired', 'not_found', name='vpsstatus'), nullable=False, server_default='creating'),
        sa.Column('provider_status', sa.String(64), nullable=True),
        sa.Column('container_id', sa.String(128), nullable=True),
        sa.Column('image_id', sa.String(128), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('expires_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('expires_hours', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('expires_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('uptime_start', sa.DateTime(), nullable=True),
        sa.Column('restart_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_restart', sa.DateTime(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['vps_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['os_id'], ['operating_systems.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vps_id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_vps_instances_vps_id', 'vps_instances', ['vps_id'], unique=True)
    op.create_index('ix_vps_instances_token', 'vps_instances', ['token'], unique=True)
    op.create_index('ix_vps_instances_provider_id', 'vps_instances', ['provider_id'])
    op.create_index('ix_vps_instances_owner_status', 'vps_instances', ['owner_id', 'status'])

    op.create_table(
        'api_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('token_hash', sa.String(128), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('last_used', sa.DateTime(), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_api_tokens_user_id', 'api_tokens', ['user_id'])

    op.create_table(
        'rdp_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vps_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('not_created', 'creating', 'docker_starting', 'docker_ready', 'selecting_tunnel', 'tunnel_creating', 'ready', 'online', 'offline', 'error', 'stopping', 'removing', name='rdpstatus'), nullable=False, server_default='not_created'),
        sa.Column('docker_container_id', sa.String(128), nullable=True),
        sa.Column('docker_container_name', sa.String(128), nullable=True),
        sa.Column('docker_image', sa.String(128), nullable=True),
        sa.Column('internal_host', sa.String(64), nullable=False, server_default='localhost'),
        sa.Column('internal_port', sa.Integer(), nullable=False, server_default='6080'),
        sa.Column('tunnel_provider', sa.Enum('trycloudflare', 'pinggy', name='tunnelprovider'), nullable=True),
        sa.Column('tunnel_status', sa.Enum('stopped', 'starting', 'running', 'error', 'reconnecting', name='tunnelstatus'), nullable=False, server_default='stopped'),
        sa.Column('tunnel_url', sa.String(256), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_started_at', sa.DateTime(), nullable=True),
        sa.Column('last_stopped_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vps_id'], ['vps_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vps_id'),
    )
    op.create_index('ix_rdp_instances_vps_id', 'rdp_instances', ['vps_id'], unique=True)
    op.create_index('ix_rdp_instances_owner_id', 'rdp_instances', ['owner_id'])

    op.create_table(
        'rdp_tunnels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rdp_instance_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.Enum('trycloudflare', 'pinggy', name='tunnelprovider'), nullable=False),
        sa.Column('status', sa.Enum('stopped', 'starting', 'running', 'error', 'reconnecting', name='tunnelstatus'), nullable=False, server_default='stopped'),
        sa.Column('public_url', sa.String(256), nullable=True),
        sa.Column('process_id', sa.Integer(), nullable=True),
        sa.Column('process_pid', sa.Integer(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['rdp_instance_id'], ['rdp_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'vps_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vps_id', sa.Integer(), nullable=False),
        sa.Column('cpu_percent', sa.Float(), nullable=False, server_default='0'),
        sa.Column('memory_percent', sa.Float(), nullable=False, server_default='0'),
        sa.Column('disk_percent', sa.Float(), nullable=False, server_default='0'),
        sa.Column('network_in_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('network_out_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['vps_id'], ['vps_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_vps_metrics_vps_id', 'vps_metrics', ['vps_id'])
    op.create_index('ix_vps_metrics_vps_time', 'vps_metrics', ['vps_id', 'timestamp'])

    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('job_type', sa.Enum('vps_create', 'vps_delete', 'vps_rebuild', 'vps_start', 'vps_stop', 'vps_restart', 'rdp_install', 'rdp_restart', 'rdp_stop', 'rdp_remove', 'tunnel_create', 'tunnel_stop', 'tunnel_restart', 'tunnel_change', 'metrics_sync', name='jobtype'), nullable=False),
        sa.Column('status', sa.Enum('queued', 'running', 'completed', 'failed', 'cancelled', name='jobstatus'), nullable=False, server_default='queued'),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('vps_id', sa.Integer(), nullable=True),
        sa.Column('rdp_id', sa.Integer(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('result', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vps_id'], ['vps_instances.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rdp_id'], ['rdp_instances.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id'),
    )
    op.create_index('ix_jobs_job_id', 'jobs', ['job_id'], unique=True)
    op.create_index('ix_jobs_user_id', 'jobs', ['user_id'])
    op.create_index('ix_jobs_vps_id', 'jobs', ['vps_id'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])

    op.create_table(
        'job_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('level', sa.String(16), nullable=False, server_default='info'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_job_logs_job_id', 'job_logs', ['job_id'])

    op.create_table(
        'terminal_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('vps_id', sa.Integer(), nullable=False),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(32), nullable=False, server_default='active'),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('last_activity', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vps_id'], ['vps_instances.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id'),
    )
    op.create_index('ix_terminal_sessions_session_id', 'terminal_sessions', ['session_id'], unique=True)
    op.create_index('ix_terminal_sessions_user_id', 'terminal_sessions', ['user_id'])

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('vps_id', sa.Integer(), nullable=True),
        sa.Column('rdp_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(256), nullable=True),
        sa.Column('result', sa.String(16), nullable=False, server_default='success'),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vps_id'], ['vps_instances.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rdp_id'], ['rdp_instances.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_vps_id', 'audit_logs', ['vps_id'])
    op.create_index('ix_audit_logs_rdp_id', 'audit_logs', ['rdp_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])
    op.create_index('ix_audit_logs_user_time', 'audit_logs', ['user_id', 'timestamp'])


def downgrade():
    op.drop_table('audit_logs')
    op.drop_table('terminal_sessions')
    op.drop_table('job_logs')
    op.drop_table('jobs')
    op.drop_table('vps_metrics')
    op.drop_table('rdp_tunnels')
    op.drop_table('rdp_instances')
    op.drop_table('api_tokens')
    op.drop_table('vps_instances')
    op.drop_table('settings')
    op.drop_table('hosts')
    op.drop_table('operating_systems')
    op.drop_table('vps_plans')
    op.drop_table('users')