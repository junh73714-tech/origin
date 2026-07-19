import { Tag } from 'antd';
import type { Citation } from '@/types/chat';

interface CitationBadgeProps {
  citation: Citation;
  onOpen: (citationId: string) => void;
}

/** 引用角标：点击按 citation_id 打开详情抽屉 */
export function CitationBadge({ citation, onOpen }: CitationBadgeProps) {
  return (
    <Tag
      color="blue"
      style={{ cursor: 'pointer' }}
      onClick={() => onOpen(citation.citation_id)}
      role="button"
      aria-label={`引用 ${citation.index}：${citation.document_name}`}
    >
      [{citation.index}] {citation.document_name}
    </Tag>
  );
}
