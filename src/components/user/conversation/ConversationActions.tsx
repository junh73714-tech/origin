import { Button, Dropdown, Modal } from 'antd';
import { MoreOutlined, ExclamationCircleOutlined } from '@ant-design/icons';
import type { Conversation } from '@/types/chat';

interface ConversationActionsProps {
  conversation: Conversation;
  onRename: (id: string) => void;
  onArchive: (id: string, archived: boolean) => void;
  onDelete: (id: string) => void;
}

/** 会话操作：重命名、归档、删除（删除与归档需二次确认） */
export function ConversationActions({
  conversation,
  onRename,
  onArchive,
  onDelete,
}: ConversationActionsProps) {
  const confirmDelete = () => {
    Modal.confirm({
      title: '确认删除该会话？',
      icon: <ExclamationCircleOutlined />,
      content: '删除后无法恢复。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => onDelete(conversation.conversation_id),
    });
  };

  const confirmArchive = () => {
    const toArchived = !conversation.archived;
    Modal.confirm({
      title: toArchived ? '确认归档该会话？' : '确认取消归档？',
      icon: <ExclamationCircleOutlined />,
      okText: '确认',
      cancelText: '取消',
      onOk: () => onArchive(conversation.conversation_id, toArchived),
    });
  };

  return (
    <Dropdown
      trigger={['click']}
      menu={{
        items: [
          { key: 'rename', label: '重命名' },
          { key: 'archive', label: conversation.archived ? '取消归档' : '归档' },
          { key: 'delete', label: '删除', danger: true },
        ],
        onClick: ({ key, domEvent }) => {
          domEvent.stopPropagation();
          if (key === 'rename') onRename(conversation.conversation_id);
          else if (key === 'archive') confirmArchive();
          else if (key === 'delete') confirmDelete();
        },
      }}
    >
      <Button
        type="text"
        size="small"
        icon={<MoreOutlined />}
        aria-label="会话操作"
        onClick={(e) => e.stopPropagation()}
      />
    </Dropdown>
  );
}
