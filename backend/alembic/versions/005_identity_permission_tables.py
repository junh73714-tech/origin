"""
成员4：添加身份认证、组织管理、数据权限和审计相关表
包括部门、用户组、数据范围、临时授权、登录日志等
"""

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


import alembic.op as op


def upgrade() -> None:
    from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey, JSON
    from sqlalchemy.sql import func

    # Departments - 部门表
    op.create_table(
        'departments',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('name', String(100), nullable=False),
        Column('code', String(50), nullable=False, unique=True, index=True),
        Column('parent_id', String(64), ForeignKey('departments.id', ondelete='SET NULL')),
        Column('description', Text),
        Column('status', String(50), nullable=False, default='active'),
        Column('sort_order', Integer, nullable=False, default=0),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_departments_parent', 'departments', ['parent_id'])

    # User Groups - 用户组表
    op.create_table(
        'user_groups',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('name', String(100), nullable=False),
        Column('code', String(50), nullable=False, unique=True, index=True),
        Column('description', Text),
        Column('status', String(50), nullable=False, default='active'),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )

    # User-Department association - 用户部门关联表
    op.create_table(
        'user_departments',
        Column('user_id', String(64), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        Column('department_id', String(64), ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True),
        Column('is_primary', Boolean, nullable=False, default=False),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
    op.create_index('ix_user_departments_department', 'user_departments', ['department_id'])

    # User-Group Member association - 用户组成员关联表
    op.create_table(
        'user_group_members',
        Column('user_id', String(64), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        Column('group_id', String(64), ForeignKey('user_groups.id', ondelete='CASCADE'), primary_key=True),
        Column('joined_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    )
    op.create_index('ix_user_group_members_group', 'user_group_members', ['group_id'])

    # Data Scopes - 数据范围表
    op.create_table(
        'data_scopes',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('name', String(100), nullable=False),
        Column('code', String(50), nullable=False, unique=True, index=True),
        Column('scope_type', String(50), nullable=False),
        Column('description', Text),
        Column('status', String(50), nullable=False, default='active'),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )

    # Knowledge Base Permissions - 知识库权限表
    op.create_table(
        'knowledge_base_permissions',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('knowledge_base_id', String(64), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('user_id', String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        Column('role_id', String(64), ForeignKey('roles.id', ondelete='CASCADE'), nullable=True),
        Column('department_id', String(64), ForeignKey('departments.id', ondelete='CASCADE'), nullable=True),
        Column('group_id', String(64), ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=True),
        Column('permission_type', String(50), nullable=False),
        Column('is_deny', Boolean, nullable=False, default=False),
        Column('effective_time', DateTime(timezone=True)),
        Column('expiration_time', DateTime(timezone=True)),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_kb_permissions_user', 'knowledge_base_permissions', ['user_id'])
    op.create_index('ix_kb_permissions_role', 'knowledge_base_permissions', ['role_id'])

    # Document Permissions - 文档权限表
    op.create_table(
        'document_permissions',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('document_id', String(64), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('user_id', String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        Column('role_id', String(64), ForeignKey('roles.id', ondelete='CASCADE'), nullable=True),
        Column('department_id', String(64), ForeignKey('departments.id', ondelete='CASCADE'), nullable=True),
        Column('group_id', String(64), ForeignKey('user_groups.id', ondelete='CASCADE'), nullable=True),
        Column('permission_type', String(50), nullable=False),
        Column('is_deny', Boolean, nullable=False, default=False),
        Column('confidentiality_level', Integer, nullable=False, default=0),
        Column('effective_time', DateTime(timezone=True)),
        Column('expiration_time', DateTime(timezone=True)),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_doc_permissions_user', 'document_permissions', ['user_id'])
    op.create_index('ix_doc_permissions_role', 'document_permissions', ['role_id'])

    # Temporary Grants - 临时授权表
    op.create_table(
        'temporary_grants',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('user_id', String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('resource_type', String(50), nullable=False),
        Column('resource_id', String(64), nullable=False),
        Column('permission_type', String(50), nullable=False),
        Column('reason', Text),
        Column('effective_time', DateTime(timezone=True), nullable=False),
        Column('expiration_time', DateTime(timezone=True), nullable=False),
        Column('status', String(50), nullable=False, default='active'),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_temporary_grants_expiration', 'temporary_grants', ['expiration_time'])

    # Login Logs - 登录日志表
    op.create_table(
        'login_logs',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('user_id', String(64), ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        Column('username', String(100), nullable=False),
        Column('success', Boolean, nullable=False),
        Column('failure_reason', String(200)),
        Column('ip_address', String(45)),
        Column('user_agent', String(500)),
        Column('login_time', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('session_id', String(64), ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    )
    op.create_index('ix_login_logs_time', 'login_logs', ['login_time'])
    op.create_index('ix_login_logs_user_success', 'login_logs', ['user_id', 'success'])


def downgrade() -> None:
    op.drop_table('login_logs')
    op.drop_table('temporary_grants')
    op.drop_table('document_permissions')
    op.drop_table('knowledge_base_permissions')
    op.drop_table('data_scopes')
    op.drop_table('user_group_members')
    op.drop_table('user_departments')
    op.drop_table('user_groups')
    op.drop_table('departments')