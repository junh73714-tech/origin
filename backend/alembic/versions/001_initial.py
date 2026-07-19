# Initial migration
# Creates all tables for the RAG Knowledge Platform

import alembic.op as op

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import Column, String, Boolean, Integer, Text, DateTime, ForeignKey, JSON
    from sqlalchemy.dialects.postgresql import Float
    from sqlalchemy.sql import func

    # Tenants
    op.create_table(
        'tenants',
        Column('id', String(64), primary_key=True),
        Column('name', String(255), nullable=False),
        Column('status', String(50), nullable=False, default='active'),
        Column('settings', JSON),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_tenants_status', 'tenants', ['status'])

    # Users
    op.create_table(
        'users',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('email', String(255), nullable=False, unique=True),
        Column('username', String(100), nullable=False, unique=True),
        Column('password_hash', String(255), nullable=False),
        Column('full_name', String(100)),
        Column('phone', String(20)),
        Column('is_active', Boolean, nullable=False, default=True),
        Column('is_superuser', Boolean, nullable=False, default=False),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_users_tenant_status', 'users', ['tenant_id', 'is_active'])

    # Permissions
    op.create_table(
        'permissions',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('name', String(100), nullable=False),
        Column('code', String(100), nullable=False, unique=True),
        Column('resource_type', String(50), nullable=False),
        Column('action', String(50), nullable=False),
        Column('description', Text),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_permissions_code', 'permissions', ['code'])

    # Roles
    op.create_table(
        'roles',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('name', String(100), nullable=False),
        Column('code', String(100), nullable=False, unique=True),
        Column('description', Text),
        Column('is_system', Boolean, nullable=False, default=False),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_roles_code', 'roles', ['code'])

    # User-Role association
    op.create_table(
        'user_roles',
        Column('user_id', String(64), ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        Column('role_id', String(64), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    )

    # Role-Permission association
    op.create_table(
        'role_permissions',
        Column('role_id', String(64), ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        Column('permission_id', String(64), ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    )

    # Sessions
    op.create_table(
        'sessions',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('user_id', String(64), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        Column('refresh_token', String(500), nullable=False),
        Column('expires_at', DateTime(timezone=True), nullable=False),
        Column('user_agent', String(255)),
        Column('ip_address', String(45)),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )

    # Knowledge Bases
    op.create_table(
        'knowledge_bases',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('name', String(255), nullable=False),
        Column('description', Text),
        Column('icon', String(255)),
        Column('is_public', Boolean, nullable=False, default=False),
        Column('settings', JSON),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_knowledge_bases_tenant_name', 'knowledge_bases', ['tenant_id', 'name'])

    # Documents
    op.create_table(
        'documents',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('knowledge_base_id', String(64), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('name', String(255), nullable=False),
        Column('file_type', String(50), nullable=False),
        Column('file_size', Integer, nullable=False),
        Column('file_path', String(500), nullable=False),
        Column('status', String(50), nullable=False, default='pending'),
        Column('char_count', Integer),
        Column('metadata', JSON),
        Column('current_version', Integer, nullable=False, default=1),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_documents_tenant_status', 'documents', ['tenant_id', 'status'])

    # Document Versions
    op.create_table(
        'document_versions',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('document_id', String(64), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('version', Integer, nullable=False),
        Column('file_path', String(500), nullable=False),
        Column('file_size', Integer, nullable=False),
        Column('change_summary', Text),
        Column('is_active', Boolean, nullable=False, default=True),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_document_versions_doc_version', 'document_versions', ['document_id', 'version'], unique=True)

    # Document Chunks
    op.create_table(
        'document_chunks',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('document_id', String(64), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('version', Integer, nullable=False),
        Column('content', Text, nullable=False),
        Column('content_hash', String(64), nullable=False, index=True),
        Column('chunk_index', Integer, nullable=False),
        Column('char_start', Integer, nullable=False),
        Column('char_end', Integer, nullable=False),
        Column('metadata', JSON),
        Column('index_status', String(50), nullable=False, default='pending'),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_document_chunks_doc_index', 'document_chunks', ['document_id', 'chunk_index'])
    op.create_index('ix_document_chunks_hash', 'document_chunks', ['content_hash'])

    # Index Tasks
    op.create_table(
        'index_tasks',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('document_id', String(64), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('task_type', String(50), nullable=False),
        Column('status', String(50), nullable=False, default='pending'),
        Column('progress', Integer, nullable=False, default=0),
        Column('total_chunks', Integer, nullable=False, default=0),
        Column('indexed_chunks', Integer, nullable=False, default=0),
        Column('error_message', Text),
        Column('started_at', String(50)),
        Column('completed_at', String(50)),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_index_tasks_status', 'index_tasks', ['status'])

    # Standard QAs
    op.create_table(
        'standard_qas',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('knowledge_base_id', String(64), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('question', Text, nullable=False),
        Column('answer', Text, nullable=False),
        Column('keywords', JSON),
        Column('category', String(100), index=True),
        Column('status', String(50), nullable=False, default='draft'),
        Column('priority', Integer, nullable=False, default=0),
        Column('view_count', Integer, nullable=False, default=0),
        Column('use_count', Integer, nullable=False, default=0),
        Column('metadata', JSON),
        Column('published_at', String(50)),
        Column('expired_at', String(50)),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_standard_qas_status_category', 'standard_qas', ['status', 'category'])

    # Candidate QAs
    op.create_table(
        'candidate_qas',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('standard_qa_id', String(64), ForeignKey('standard_qas.id', ondelete='CASCADE'), nullable=True, index=True),
        Column('knowledge_base_id', String(64), ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('question', Text, nullable=False),
        Column('answer', Text, nullable=False),
        Column('source', String(50), nullable=False),
        Column('source_session_id', String(64)),
        Column('confidence', Float),
        Column('status', String(50), nullable=False, default='pending'),
        Column('review_comment', Text),
        Column('reviewed_at', String(50)),
        Column('metadata', JSON),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )

    # QA References
    op.create_table(
        'qa_references',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('qa_id', String(64), ForeignKey('standard_qas.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('document_id', String(64), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        Column('chunk_id', String(64), ForeignKey('document_chunks.id', ondelete='CASCADE'), nullable=False),
        Column('relevance_score', Float, nullable=False),
        Column('quote_text', Text),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_qa_references_qa_doc', 'qa_references', ['qa_id', 'document_id'])

    # QA Audit Records
    op.create_table(
        'qa_audit_records',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('qa_id', String(64), ForeignKey('standard_qas.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('action', String(50), nullable=False),
        Column('status_from', String(50)),
        Column('status_to', String(50)),
        Column('comment', Text),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )

    # Conversations
    op.create_table(
        'conversations',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('user_id', String(64), nullable=False, index=True),
        Column('session_id', String(64), index=True),
        Column('title', String(255)),
        Column('status', String(50), nullable=False, default='active'),
        Column('metadata', JSON),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_conversations_user_status', 'conversations', ['user_id', 'status'])

    # Messages
    op.create_table(
        'messages',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('conversation_id', String(64), ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('role', String(20), nullable=False),
        Column('content', Text, nullable=False),
        Column('intent', String(100)),
        Column('matched_qa_id', String(64), ForeignKey('standard_qas.id', ondelete='SET NULL'), nullable=True),
        Column('confidence', Float),
        Column('references', JSON),
        Column('feedback', String(50)),
        Column('feedback_comment', Text),
        Column('metadata', JSON),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )

    # User Feedbacks
    op.create_table(
        'user_feedbacks',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('message_id', String(64), ForeignKey('messages.id', ondelete='CASCADE'), nullable=False, index=True),
        Column('feedback', String(50), nullable=False),
        Column('comment', Text),
        Column('score', Integer),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )

    # Audit Logs
    op.create_table(
        'audit_logs',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('user_id', String(64), nullable=False, index=True),
        Column('action', String(100), nullable=False, index=True),
        Column('resource_type', String(50), nullable=False),
        Column('resource_id', String(64), index=True),
        Column('request_id', String(100), index=True),
        Column('ip_address', String(45)),
        Column('user_agent', String(500)),
        Column('method', String(10)),
        Column('path', String(500)),
        Column('status_code', Integer),
        Column('duration_ms', Integer),
        Column('request_body', JSON),
        Column('response_body', JSON),
        Column('details', JSON),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_audit_logs_tenant_time', 'audit_logs', ['tenant_id', 'created_at'])
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'])

    # Security Events
    op.create_table(
        'security_events',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('event_type', String(100), nullable=False, index=True),
        Column('severity', String(20), nullable=False),
        Column('user_id', String(64), index=True),
        Column('ip_address', String(45)),
        Column('description', Text, nullable=False),
        Column('details', JSON),
        Column('resolved', Boolean, nullable=False, default=False),
        Column('resolved_at', String(50)),
        Column('resolved_by', String(64)),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_security_events_severity_resolved', 'security_events', ['severity', 'resolved'])
    op.create_index('ix_security_events_time', 'security_events', ['created_at'])

    # Outbox Events
    op.create_table(
        'outbox_events',
        Column('id', String(64), primary_key=True),
        Column('tenant_id', String(64), nullable=False, index=True),
        Column('event_type', String(100), nullable=False, index=True),
        Column('aggregate_type', String(50), nullable=False),
        Column('aggregate_id', String(64), nullable=False, index=True),
        Column('payload', JSON, nullable=False),
        Column('published', Boolean, nullable=False, default=False),
        Column('published_at', String(50)),
        Column('retry_count', Integer, nullable=False, default=0),
        Column('max_retries', Integer, nullable=False, default=3),
        Column('error_message', Text),
        Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
        Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        Column('created_by', String(64), nullable=False),
        Column('updated_by', String(64)),
    )
    op.create_index('ix_outbox_events_unpublished', 'outbox_events', ['published', 'created_at'])


def downgrade() -> None:
    op.drop_table('outbox_events')
    op.drop_table('security_events')
    op.drop_table('audit_logs')
    op.drop_table('user_feedbacks')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('qa_audit_records')
    op.drop_table('qa_references')
    op.drop_table('candidate_qas')
    op.drop_table('standard_qas')
    op.drop_table('index_tasks')
    op.drop_table('document_chunks')
    op.drop_table('document_versions')
    op.drop_table('documents')
    op.drop_table('knowledge_bases')
    op.drop_table('sessions')
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_table('users')
    op.drop_table('tenants')
