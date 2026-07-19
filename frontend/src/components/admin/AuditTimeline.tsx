/**
 * 管理后台公共组件 - 审计时间线
 * 成员3：管理后台前端
 * 展示操作审计记录的时间线视图
 */
import { Timeline, Typography, Tag, Space, Descriptions } from 'antd';
import {
  AuditOutlined,
  UserOutlined,
  SafetyOutlined,
  FileTextOutlined,
  SettingOutlined,
  LoginOutlined,
} from '@ant-design/icons';
import type { OperationLog } from '@/types/admin';

const { Text } = Typography;

/** 资源类型图标映射 */
const RESOURCE_ICON_MAP: Record<string, React.ReactNode> = {
  user: <UserOutlined />,
  role: <SafetyOutlined />,
  permission: <SafetyOutlined />,
  knowledge_base: <FileTextOutlined />,
  document: <FileTextOutlined />,
  qa: <FileTextOutlined />,
  config: <SettingOutlined />,
  auth: <LoginOutlined />,
};

export interface AuditTimelineProps {
  /** 操作日志列表 */
  items: OperationLog[];
  /** 是否显示资源详情 */
  showResourceDetail?: boolean;
  /** 时间线位置 */
  position?: 'left' | 'right' | 'alternate';
}

/**
 * 审计时间线组件
 * 用于查看操作日志、登录日志、权限审计记录
 */
export function AuditTimeline({
  items,
  showResourceDetail = false,
  position = 'left',
}: AuditTimelineProps) {
  if (items.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Text type="secondary">暂无审计记录</Text>
      </div>
    );
  }

  return (
    <Timeline
      mode={position}
      items={items.map((item) => ({
        dot: RESOURCE_ICON_MAP[item.resource_type] || <AuditOutlined />,
        children: (
          <div>
            {/* 操作概述 */}
            <Space>
              <Text strong>{item.user_name}</Text>
              <Text type="secondary">{item.action}</Text>
              <Text>{item.resource_name || item.resource_id}</Text>
              <Tag color={item.status_code >= 400 ? 'red' : 'green'}>
                {item.status_code}
              </Tag>
            </Space>

            {/* 详细信息 */}
            {showResourceDetail && (
              <Descriptions
                size="small"
                column={2}
                style={{ marginTop: 8, padding: 8, background: '#fafafa', borderRadius: 4 }}
              >
                <Descriptions.Item label="资源类型">
                  {item.resource_type}
                </Descriptions.Item>
                <Descriptions.Item label="资源ID">
                  {item.resource_id}
                </Descriptions.Item>
                <Descriptions.Item label="IP地址">
                  {item.ip_address}
                </Descriptions.Item>
                <Descriptions.Item label="耗时">
                  {item.duration_ms ? `${item.duration_ms}ms` : '-'}
                </Descriptions.Item>
                <Descriptions.Item label="Trace ID" span={2}>
                  <Text code>{item.trace_id}</Text>
                </Descriptions.Item>
              </Descriptions>
            )}

            {/* 时间戳 */}
            <div style={{ marginTop: 4 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {item.created_at}
              </Text>
            </div>
          </div>
        ),
      }))}
    />
  );
}