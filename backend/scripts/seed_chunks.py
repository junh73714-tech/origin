"""补联调数据：Chunk + IndexTask"""
import os,asyncio,uuid
from datetime import datetime,timezone

# 数据库连接信息从环境变量读取，不硬编码密码
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import async_session_factory
from sqlalchemy import text

NOW = datetime.now(timezone.utc)
VER_ID = '9000a025-b484-4222-9ae9-ff566da5aecf'
DOC_ID = 'a7257edf-a177-43bd-bce4-359376246b72'
KB_ID = 'f3f6423e-f705-4abb-86ba-a7ff928e2074'
TID = '592917f4-0c06-5990-ac34-486d03bf7791'
UID = '8e7e5721-f4f0-56ae-b11c-825e410e93c8'

CHUNKS = [
    {"no":1,"title":"第一章 总则","raw":"第一条 目的\n为规范公司考勤管理，维护正常工作秩序，保障员工合法权益，特制定本制度。","clean":"第一条 目的 为规范公司考勤管理，维护正常工作秩序，保障员工合法权益，特制定本制度。"},
    {"no":2,"title":"第一条 目的","raw":"本制度适用于公司全体员工，包括试用期员工和实习生。","clean":"第二条 适用范围 本制度适用于公司全体员工，包括试用期员工和实习生。"},
    {"no":3,"title":"第二章 工作时间","raw":"第三条 标准工时\n公司实行每周五天工作制。上午9:00-12:00，下午13:30-18:00。","clean":"第三条 标准工时 公司实行每周五天工作制。上午9:00-12:00，下午13:30-18:00。"},
]

async def seed():
    async with async_session_factory() as db:
        for c in CHUNKS:
            ch_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO document_chunks (id, tenant_id, knowledge_base_id, document_id,
                    document_version_id, version, chunk_no, title_path, content, clean_text,
                    content_hash, chunk_index, char_start, char_end, token_count,
                    permission_metadata, status, index_status, created_by, created_at, updated_at)
                VALUES (:id, :tid, :kb, :doc, :ver, 1, :no, :title, :raw, :clean,
                    :hash, :no, 0, 100, :tokens, :perm, 'active', 'indexed', :uid, :now, :now)
            """), {"id":ch_id,"tid":TID,"kb":KB_ID,"doc":DOC_ID,"ver":VER_ID,
                   "no":c["no"],"title":c["title"],"raw":c["raw"],"clean":c["clean"],
                   "hash":str(uuid.uuid4())[:16],"tokens":len(c["clean"])//2,"perm":'{"scope_hash":"test"}',
                   "uid":UID,"now":NOW})
            # index_task - opensearch
            await db.execute(text("""
                INSERT INTO index_tasks (id, tenant_id, document_id, document_version_id,
                    chunk_id, task_type, target, idempotent_key, status, retry_count,
                    total_chunks, indexed_chunks, created_by, created_at, updated_at)
                VALUES (:id, :tid, :doc, :ver, :ch, 'create', 'opensearch', :ik, 'completed', 0,
                    1, 1, :uid, :now, :now)
            """), {"id":str(uuid.uuid4()),"tid":TID,"doc":DOC_ID,"ver":VER_ID,"ch":ch_id,
                   "ik":str(uuid.uuid4())[:32],"uid":UID,"now":NOW})
            # index_task - pgvector
            await db.execute(text("""
                INSERT INTO index_tasks (id, tenant_id, document_id, document_version_id,
                    chunk_id, task_type, target, idempotent_key, status, retry_count,
                    total_chunks, indexed_chunks, created_by, created_at, updated_at)
                VALUES (:id, :tid, :doc, :ver, :ch, 'create', 'pgvector', :ik, 'completed', 0,
                    1, 1, :uid, :now, :now)
            """), {"id":str(uuid.uuid4()),"tid":TID,"doc":DOC_ID,"ver":VER_ID,"ch":ch_id,
                   "ik":str(uuid.uuid4())[:32],"uid":UID,"now":NOW})

        await db.commit()
        print(f"Created {len(CHUNKS)} chunks + {len(CHUNKS)*2} index_tasks")

asyncio.run(seed())
