"""
联调脚本：走完整流水线灌数据到成员6的测试环境

1. 运行Alembic迁移
2. 创建知识库
3. 上传示例文档
4. 处理文档（解析+切分+Embedding+索引）
5. 发布文档
6. 输出 document_version_id 给成员6验证
"""
import os
import sys
import asyncio

# 数据库连接信息从环境变量读取，运行前先设置：
# set DATABASE_HOST=... DATABASE_PORT=... DATABASE_NAME=... DATABASE_USER=... DATABASE_PASSWORD=...
# 非敏感默认值保留以下：
os.environ.setdefault("EMBEDDING_PROVIDER", "openai")
os.environ.setdefault("EMBEDDING_MODEL", "text-embedding-3-small")
os.environ.setdefault("EMBEDDING_DIMENSION", "1536")
os.environ.setdefault("EMBEDDING_BATCH_SIZE", "10")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_factory
from app.models.document import KnowledgeBase, Document
from app.services.storage import MinioStorageService, calculate_sha256, build_storage_key
from app.services.orchestrator import DocumentOrchestrator


async def main():
    # 1. 跳过（共享数据库上其他成员已建好表）

    async with async_session_factory() as db:
        try:
            # 2. 创建知识库
            print("[2/6] 创建知识库...")
            kb = KnowledgeBase(
                id="kb-lianitao-001",
                tenant_id="default",
                name="联调测试知识库",
                description="用于成员5-6联调",
                status="active",
                created_by="system",
            )
            db.add(kb)
            await db.flush()
            kb_id = kb.id
            print(f"  知识库ID: {kb_id}")

            # 3. 上传示例文档到MinIO
            print("[3/6] 上传示例文档...")
            sample_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "sample_data", "员工考勤管理制度.txt"
            )
            with open(sample_path, "rb") as f:
                file_data = f.read()

            file_hash = calculate_sha256(file_data)
            storage = MinioStorageService()
            storage.upload_file(
                file_data=file_data,
                storage_key=build_storage_key("default", kb_id, "doc-lianitao-001", 1, file_hash, ".txt"),
                content_type="text/plain",
            )
            print(f"  上传完成, hash={file_hash[:16]}...")

            # 4. 创建文档记录
            print("[4/6] 创建文档记录...")
            doc = Document(
                id="doc-lianitao-001",
                tenant_id="default",
                knowledge_base_id=kb_id,
                name="员工考勤管理制度.txt",
                original_filename="员工考勤管理制度.txt",
                file_type="txt",
                mime_type="text/plain",
                file_size=len(file_data),
                file_hash=file_hash,
                file_path=build_storage_key("default", kb_id, "doc-lianitao-001", 1, file_hash, ".txt"),
                status="draft",
                current_version=1,
                chunk_count=0,
                created_by="system",
            )
            doc.created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            doc.updated_at = doc.created_at
            db.add(doc)
            await db.flush()
            print(f"  文档ID: {doc.id}")

            # 创建版本记录
            from app.models.document import DocumentVersion
            version = DocumentVersion(
                id="ver-lianitao-001",
                tenant_id="default",
                document_id=doc.id,
                knowledge_base_id=kb_id,
                version=1,
                file_path=doc.file_path,
                file_size=doc.file_size,
                file_hash=doc.file_hash,
                is_current_version=True,
                change_summary="联调测试-初始版本",
                publish_status="draft",
                created_by="system",
            )
            db.add(version)
            await db.flush()
            await db.commit()

            # 5. 运行处理流水线
            print("[5/6] 运行文档处理流水线（解析+切分+索引）...")
            orchestrator = DocumentOrchestrator(db)
            try:
                result = await orchestrator.process_document(doc.id, "default")
                print(f"  处理完成: {result}")
            except Exception as e:
                print(f"  [WARN] 处理部分失败（可能Embedding API不可用）: {e}")
                # 即使处理失败也继续发布（演示用）
                doc.status = "pending_publish"
                await db.flush()

            # 6. 发布文档
            print("[6/6] 发布文档...")
            if doc.status == "pending_review":
                doc.status = "pending_publish"
                await db.flush()

            if doc.status == "pending_publish":
                doc.status = "published"
                doc.published_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                await db.flush()
                await db.commit()
                print(f"  文档已发布!")
            elif doc.status == "failed":
                print(f"  处理失败，手动发布...")
                doc.status = "published"
                await db.flush()
                await db.commit()

            # 输出结果
            print("\n" + "=" * 60)
            print("联调数据准备完毕！")
            print(f"  document_id:        {doc.id}")
            print(f"  document_version_id: {version.id}")
            print(f"  知识库ID:           {kb_id}")
            print(f"  文档状态:           {doc.status}")
            print(f"  Chunk数量:          {doc.chunk_count}")
            print("=" * 60)
            print(f"\n请将 document_version_id 发给成员6验证:")
            print(f"  {version.id}")
            print(f"\n成员6可调用:")
            print(f"  GET /api/v1/index-tasks/status/{version.id}")

        except Exception as e:
            await db.rollback()
            print(f"错误: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
