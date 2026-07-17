/**
 * 管理后台公共组件 - 详情抽屉
 * 成员3：管理后台前端
 * 右侧滑出的详情抽屉，用于展示列表项的详细信息
 */
import { Drawer, Descriptions, Typography, Space } from 'antd';
import { CloseOutlined } from '@ant-design/icons';
import type { DescriptionsProps } from 'antd';

const { Title } = Typography;

export interface DetailDrawerProps {
  /** 抽屉是否可见 */
  open: boolean;
  /** 关闭回调 */
  onClose: () => void;
  /** 详情标题 */
  title: string;
  /** 详情数据项 */
  items: DescriptionsProps['items'];
  /** 抽屉宽度 */
  width?: number | string;
  /** 是否加载中 */
  loading?: boolean;
  /** 底部操作按钮 */
  footerActions?: React.ReactNode;
  /** 顶部额外信息 */
  extra?: React.ReactNode;
  /** 描述列表列数 */
  column?: number;
}

/**
 * 详情抽屉组件
 * 右侧滑出，展示列表项的详细信息
 * 使用 Descriptions 组件统一格式
 */
export function DetailDrawer({
  open,
  onClose,
  title,
  items,
  width = 600,
  loading = false,
  footerActions,
  extra,
  column = 2,
}: DetailDrawerProps) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Title level={5} style={{ margin: 0 }}>{title}</Title>
          {extra}
        </Space>
      }
      width={width}
      loading={loading}
      closeIcon={<CloseOutlined />}
      destroyOnClose
      footer={
        footerActions ? (
          <Space style={{ justifyContent: 'flex-end', width: '100%' }}>
            {footerActions}
          </Space>
        ) : undefined
      }
    >
      <Descriptions
        items={items}
        column={column}
        layout="vertical"
        size="middle"
        labelStyle={{ fontWeight: 500, color: '#666' }}
        contentStyle={{ color: '#1f1f1f' }}
      />
    </Drawer>
  );
}