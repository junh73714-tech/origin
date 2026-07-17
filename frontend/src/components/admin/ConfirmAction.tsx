/**
 * 管理后台公共组件 - 操作确认弹窗
 * 成员3：管理后台前端
 * 高风险操作二次确认，展示影响范围说明
 */
import { Modal, Typography, Alert, Space } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

export interface ConfirmActionProps {
  /** 弹窗是否可见 */
  open: boolean;
  /** 确认标题 */
  title: string;
  /** 确认内容 */
  content: string | React.ReactNode;
  /** 是否危险操作 */
  danger?: boolean;
  /** 确认按钮文字 */
  okText?: string;
  /** 取消按钮文字 */
  cancelText?: string;
  /** 确认回调 */
  onOk: () => Promise<void> | void;
  /** 取消回调 */
  onCancel: () => void;
  /** 确认中加载状态 */
  confirmLoading?: boolean;
  /** 影响范围说明 */
  impactDescription?: string;
  /** 确认输入验证（如需要输入文字确认） */
  confirmInput?: string;
}

/**
 * 操作确认弹窗组件
 * 用于高风险操作（删除、下线、禁用等）的二次确认
 * 展示影响范围，防止误操作
 */
export function ConfirmAction({
  open,
  title,
  content,
  danger = false,
  okText = '确认',
  cancelText = '取消',
  onOk,
  onCancel,
  confirmLoading = false,
  impactDescription,
}: ConfirmActionProps) {
  return (
    <Modal
      open={open}
      title={
        <Space>
          {danger && <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
          {title}
        </Space>
      }
      onOk={onOk}
      onCancel={onCancel}
      confirmLoading={confirmLoading}
      okText={okText}
      cancelText={cancelText}
      okButtonProps={{
        danger: danger,
        type: danger ? 'primary' : 'primary',
      }}
      centered
      destroyOnClose
    >
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {/* 主要内容 */}
        <div>
          {typeof content === 'string' ? (
            <Paragraph style={{ marginBottom: 0 }}>{content}</Paragraph>
          ) : (
            content
          )}
        </div>

        {/* 影响范围说明 */}
        {impactDescription && (
          <Alert
            type="warning"
            showIcon
            message="影响说明"
            description={impactDescription}
            style={{ marginTop: 8 }}
          />
        )}

        {/* 危险操作提示 */}
        {danger && (
          <Text type="danger" style={{ fontSize: 12 }}>
            此操作不可撤销，请谨慎执行
          </Text>
        )}
      </Space>
    </Modal>
  );
}