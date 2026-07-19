import { useEffect, useState } from 'react';
import { Card, Input, Modal, Button, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useConversationStore } from '@/stores/conversation/conversationStore';
import { ConversationList } from '@/components/user/conversation/ConversationList';

/** 历史会话页：搜索、列表、重命名、归档、删除、新建 */
export function HistoryPage() {
  const navigate = useNavigate();
  const {
    list,
    loading,
    currentId,
    keyword,
    setKeyword,
    loadList,
    rename,
    archive,
    remove,
    createConversation,
    setCurrent,
  } = useConversationStore();

  const [renameTarget, setRenameTarget] = useState<string | null>(null);
  const [renameText, setRenameText] = useState('');

  useEffect(() => {
    loadList(1);
  }, [loadList]);

  const handleSelect = (id: string) => {
    setCurrent(id);
    navigate(`/chat/${id}`);
  };

  const handleRenameOpen = (id: string) => {
    const conv = list.find((c) => c.conversation_id === id);
    setRenameTarget(id);
    setRenameText(conv?.title ?? '');
  };

  const handleRenameOk = async () => {
    if (renameTarget && renameText.trim()) {
      await rename(renameTarget, renameText.trim());
    }
    setRenameTarget(null);
  };

  const handleCreate = async () => {
    const conv = await createConversation();
    navigate(`/chat/${conv.conversation_id}`);
  };

  return (
    <Card
      title="历史会话"
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建会话
        </Button>
      }
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        <Input.Search
          placeholder="搜索会话标题"
          allowClear
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onSearch={() => loadList(1)}
        />
        <ConversationList
          items={list}
          currentId={currentId}
          loading={loading}
          onSelect={handleSelect}
          onRename={handleRenameOpen}
          onArchive={archive}
          onDelete={remove}
        />
      </Space>

      <Modal
        title="重命名会话"
        open={renameTarget !== null}
        onCancel={() => setRenameTarget(null)}
        onOk={handleRenameOk}
        okText="保存"
        cancelText="取消"
      >
        <Input
          value={renameText}
          onChange={(e) => setRenameText(e.target.value)}
          placeholder="请输入会话标题"
          maxLength={50}
        />
      </Modal>
    </Card>
  );
}
