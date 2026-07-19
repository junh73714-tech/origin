"""为 qa_sources 表添加 document_version_id UUID 字段

Revision ID: 006
Revises: 005
Create Date: 2026-07-19

成员7：补充 qa_sources 表的 document_version_id 字段，使每条来源绑定可精确定位到文档版本的 UUID，
与成员5的 document_versions.id 对齐。兼容现有整型 document_version 字段。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 在 qa_sources 表中添加 document_version_id 列
    op.add_column(
        "qa_sources",
        sa.Column(
            "document_version_id",
            sa.String(64),
            nullable=True,
            comment="来源文档版本 UUID（关联 document_versions.id）",
        ),
    )
    # 为该字段创建索引以加速查询
    op.create_index(
        "ix_qa_sources_doc_version_uuid",
        "qa_sources",
        ["document_id", "document_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_qa_sources_doc_version_uuid", table_name="qa_sources")
    op.drop_column("qa_sources", "document_version_id")
