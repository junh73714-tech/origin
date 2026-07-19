import { Descriptions, Typography } from 'antd';
import type { CitationDetail } from '@/types/chat';
import { formatDateTime } from '@/utils/format';

interface SourceMetadataProps {
  detail: CitationDetail;
}

/** 引用来源元数据展示。无权限时不展示真实地址与正文。 */
export function SourceMetadata({ detail }: SourceMetadataProps) {
  return (
    <Descriptions column={1} size="small" bordered>
      <Descriptions.Item label="文档名称">{detail.document_name}</Descriptions.Item>
      {detail.title_path.length > 0 ? (
        <Descriptions.Item label="标题路径">
          {detail.title_path.join(' / ')}
        </Descriptions.Item>
      ) : null}
      {typeof detail.page_no === 'number' ? (
        <Descriptions.Item label="页码">第 {detail.page_no} 页</Descriptions.Item>
      ) : null}
      {detail.document_version ? (
        <Descriptions.Item label="文档版本">{detail.document_version}</Descriptions.Item>
      ) : null}
      {detail.effective_time ? (
        <Descriptions.Item label="生效时间">
          {formatDateTime(detail.effective_time)}
        </Descriptions.Item>
      ) : null}
      <Descriptions.Item label="来源类型">{detail.source_type}</Descriptions.Item>
      {detail.quoted_text ? (
        <Descriptions.Item label="引用原文">
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            {detail.quoted_text}
          </Typography.Paragraph>
        </Descriptions.Item>
      ) : null}
    </Descriptions>
  );
}
