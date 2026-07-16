/**
 * 公共组件 - 确认对话框
 */
import { Modal, Typography, Space } from 'antd';
import { ExclamationCircleFilled } from '@ant-design/icons';

const { Text } = Typography;

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  content: string | React.ReactNode;
  confirmText?: string;
  cancelText?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
}

export function ConfirmDialog({
  open,
  title,
  content,
  confirmText = '确定',
  cancelText = '取消',
  danger = false,
  onConfirm,
  onCancel,
  loading = false,
}: ConfirmDialogProps) {
  return (
    <Modal
      open={open}
      title={
        <Space>
          {danger && <ExclamationCircleFilled style={{ color: '#ff4d4f' }} />}
          {title}
        </Space>
      }
      okText={confirmText}
      cancelText={cancelText}
      okButtonProps={{ danger, loading }}
      onOk={onConfirm}
      onCancel={onCancel}
    >
      {typeof content === 'string' ? <Text>{content}</Text> : content}
    </Modal>
  );
}
