/**
 * 公共组件 - 空状态
 */
import { Button, Empty, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';

const { Paragraph } = Typography;

interface EmptyStateProps {
  title?: string;
  description?: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export function EmptyState({
  title = '暂无数据',
  description,
  actionText,
  onAction,
  icon,
}: EmptyStateProps) {
  return (
    <Empty
      image={icon || Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <div style={{ textAlign: 'center' }}>
          <Paragraph strong>{title}</Paragraph>
          {description && <Paragraph type="secondary">{description}</Paragraph>}
        </div>
      }
    >
      {actionText && onAction && (
        <Button type="primary" icon={<PlusOutlined />} onClick={onAction}>
          {actionText}
        </Button>
      )}
    </Empty>
  );
}
