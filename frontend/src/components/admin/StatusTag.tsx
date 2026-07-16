/**
 * 管理后台公共组件 - 状态标签
 * 成员3：管理后台前端
 * 统一的状态标签样式，用于表格、详情等场景
 */
import { Tag, type TagProps } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  SyncOutlined,
  MinusCircleOutlined,
  ExclamationCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';

/** 状态颜色映射 */
const STATUS_COLOR_MAP: Record<string, { color: TagProps['color']; icon?: React.ReactNode }> = {
  // 通用状态
  active: { color: 'green', icon: <CheckCircleOutlined /> },
  enabled: { color: 'green', icon: <CheckCircleOutlined /> },
  disabled: { color: 'default', icon: <MinusCircleOutlined /> },
  locked: { color: 'red', icon: <StopOutlined /> },
  deleted: { color: 'default', icon: <CloseCircleOutlined /> },

  // 文档状态
  pending: { color: 'default', icon: <ClockCircleOutlined /> },
  uploading: { color: 'processing', icon: <SyncOutlined spin /> },
  uploaded: { color: 'cyan', icon: <CheckCircleOutlined /> },
  parsing: { color: 'processing', icon: <SyncOutlined spin /> },
  parsed: { color: 'geekblue', icon: <CheckCircleOutlined /> },
  chunking: { color: 'processing', icon: <SyncOutlined spin /> },
  indexing: { color: 'processing', icon: <SyncOutlined spin /> },
  completed: { color: 'green', icon: <CheckCircleOutlined /> },
  failed: { color: 'red', icon: <CloseCircleOutlined /> },
  paused: { color: 'warning', icon: <PauseCircleOutlined /> },

  // 任务状态
  running: { color: 'processing', icon: <SyncOutlined spin /> },
  cancelled: { color: 'default', icon: <MinusCircleOutlined /> },

  // 问答状态
  draft: { color: 'default', icon: <ClockCircleOutlined /> },
  pending_review: { color: 'orange', icon: <ExclamationCircleOutlined /> },
  published: { color: 'green', icon: <CheckCircleOutlined /> },
  unpublished: { color: 'default', icon: <MinusCircleOutlined /> },
  expired: { color: 'default', icon: <ClockCircleOutlined /> },
  approved: { color: 'green', icon: <CheckCircleOutlined /> },
  rejected: { color: 'red', icon: <CloseCircleOutlined /> },
  revised: { color: 'blue', icon: <SyncOutlined /> },

  // 安全事件
  low: { color: 'blue' },
  medium: { color: 'orange' },
  high: { color: 'red' },
  critical: { color: 'red' },

  // 健康状态
  healthy: { color: 'green', icon: <CheckCircleOutlined /> },
  degraded: { color: 'warning', icon: <ExclamationCircleOutlined /> },
  unhealthy: { color: 'red', icon: <CloseCircleOutlined /> },

  // 审核结果
  success: { color: 'green', icon: <CheckCircleOutlined /> },
  warning: { color: 'warning', icon: <ExclamationCircleOutlined /> },
  error: { color: 'red', icon: <CloseCircleOutlined /> },

  // 开放状态
  open: { color: 'orange', icon: <ExclamationCircleOutlined /> },
  reviewing: { color: 'processing', icon: <SyncOutlined spin /> },
  resolved: { color: 'green', icon: <CheckCircleOutlined /> },
};

/** 状态标签的中文映射 */
const STATUS_LABEL_MAP: Record<string, string> = {
  // 通用
  active: '已激活',
  enabled: '已启用',
  disabled: '已禁用',
  locked: '已锁定',
  deleted: '已删除',

  // 文档
  pending: '待处理',
  uploading: '上传中',
  uploaded: '已上传',
  parsing: '解析中',
  parsed: '已解析',
  chunking: '分块中',
  indexing: '索引中',
  completed: '已完成',
  failed: '失败',
  paused: '已暂停',

  // 任务
  running: '运行中',
  cancelled: '已取消',

  // 问答
  draft: '草稿',
  pending_review: '待审核',
  published: '已发布',
  unpublished: '已下线',
  expired: '已过期',
  approved: '已通过',
  rejected: '已驳回',
  revised: '已修改',

  // 安全
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  critical: '严重',

  // 健康
  healthy: '健康',
  degraded: '降级',
  unhealthy: '异常',

  // 审核
  success: '成功',
  warning: '警告',
  error: '错误',

  // 开放状态
  open: '待处理',
  reviewing: '审核中',
  resolved: '已解决',
};

export interface StatusTagProps {
  /** 状态值 */
  status: string;
  /** 自定义标签文本，不传则使用默认映射 */
  label?: string;
  /** 自定义颜色 */
  color?: TagProps['color'];
  /** 是否显示图标 */
  showIcon?: boolean;
}

/**
 * 状态标签组件
 * 根据状态值自动匹配颜色和图标
 */
export function StatusTag({ status, label, color, showIcon = true }: StatusTagProps) {
  const config = STATUS_COLOR_MAP[status] || { color: 'default' };
  const displayLabel = label || STATUS_LABEL_MAP[status] || status;

  return (
    <Tag
      color={color || config.color}
      icon={showIcon ? config.icon : undefined}
    >
      {displayLabel}
    </Tag>
  );
}