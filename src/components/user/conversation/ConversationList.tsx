import { List, Tag, Typography } from 'antd';
import type { Conversation } from '@/types/chat';
import { formatDateTime } from '@/utils/format';
import { ConversationActions } from './ConversationActions';
import { EmptyState } from '@/components/user/common/EmptyState';

interface ConversationListProps {
  items: Conversation[];
  currentId: string | null;
  loading: boolean;
  onSelect: (id: string) => void;
  onRename: (id: string) => void;
  onArchive: (id: string, archived: boolean) => void;
  onDelete: (id: string) => void;
}

/** 会话列表：选中态、更新时间、归档标记与操作 */
export function ConversationList({
  items,
  currentId,
  loading,
  onSelect,
  onRename,
  onArchive,
  onDelete,
}: ConversationListProps) {
  if (!loading && items.length === 0) {
    return <EmptyState description="暂无历史会话" />;
  }

  return (
    <List
      loading={loading}
      dataSource={items}
      renderItem={(item) => {
        const selected = item.conversation_id === currentId;
        return (
          <List.Item
            onClick={() => onSelect(item.conversation_id)}
            style={{
              cursor: 'pointer',
              padding: '10px 12px',
              background: selected ? '#eef3ff' : undefined,
              borderRadius: 6,
            }}
            actions={[
              <ConversationActions
                key="actions"
                conversation={item}
                onRename={onRename}
                onArchive={onArchive}
                onDelete={onDelete}
              />,
            ]}
          >
            <List.Item.Meta
              title={
                <span>
                  <Typography.Text ellipsis style={{ maxWidth: 180 }}>
                    {item.title}
                  </Typography.Text>
                  {item.archived ? (
                    <Tag style={{ marginLeft: 8 }}>已归档</Tag>
                  ) : null}
                </span>
              }
              description={formatDateTime(item.updated_at)}
            />
          </List.Item>
        );
      }}
    />
  );
}
