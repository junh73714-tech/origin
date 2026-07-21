"""种子数据（匹配001→002→003新Schema）"""
import os,asyncio,uuid
from datetime import datetime,timezone

# 数据库连接信息从环境变量读取，不硬编码密码
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import async_session_factory
from sqlalchemy import text

NOW = datetime.now(timezone.utc)
KB_ID = str(uuid.uuid4())
DOC_ID = str(uuid.uuid4())
VER_ID = str(uuid.uuid4())
TID = '592917f4-0c06-5990-ac34-486d03bf7791'
UID = '8e7e5721-f4f0-56ae-b11c-825e410e93c8'

async def seed():
    async with async_session_factory() as db:
        await db.execute(text("""
            INSERT INTO knowledge_bases (id, tenant_id, name, description, status,
                business_domain, is_public, document_count, chunk_count, created_by, created_at, updated_at)
            VALUES (:id, :tid, :name, :desc, 'active', '联调测试', true, 0, 0, :uid, :now, :now)
            ON CONFLICT (id) DO NOTHING
        """), {"id": KB_ID, "tid": TID, "uid": UID, "name": "联调测试知识库", "desc": "成员5-6联调用", "now": NOW})

        await db.execute(text("""
            INSERT INTO documents (id, tenant_id, knowledge_base_id, name, original_filename,
                file_type, mime_type, file_size, file_hash, file_path, status, current_version,
                chunk_count, created_by, created_at, updated_at)
            VALUES (:id, :tid, :kb_id, :name, :name, 'txt', 'text/plain',
                100, 'e3b0c4', 'test/obj.key', 'published', 1, 0, :uid, :now, :now)
            ON CONFLICT (id) DO NOTHING
        """), {"id": DOC_ID, "tid": TID, "uid": UID, "kb_id": KB_ID, "name": "联调测试文档.txt", "now": NOW})

        await db.execute(text("""
            INSERT INTO document_versions (id, tenant_id, knowledge_base_id, document_id,
                version, file_path, file_size, file_hash, is_active, is_current_version,
                publish_status, created_by, created_at, updated_at)
            VALUES (:id, :tid, :kb_id, :doc_id, 1, 'test/obj.key', 100,
                'e3b0c4', true, true, 'published', :uid, :now, :now)
            ON CONFLICT (id) DO NOTHING
        """), {"id": VER_ID, "tid": TID, "uid": UID, "kb_id": KB_ID, "doc_id": DOC_ID, "now": NOW})

        await db.commit()
        print(f"\n========================================")
        print(f"document_version_id: {VER_ID}")
        print(f"========================================")

asyncio.run(seed())
