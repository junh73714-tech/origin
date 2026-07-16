/**
 * 管理后台公共组件 - 任务进度
 * 成员3：管理后台前端
 * 展示长任务的进度、阶段、成功/失败数等
 */
import { Progress, Steps, Typography, Tag, Space, Button, Tooltip } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

export interface TaskStage {
  /** 阶段名称 */
  name: string;
  /** 阶段状态 */
  status: 'wait' | 'process' | 'finish' | 'error';
  /** 阶段描述 */
  description?: string;
}

export interface TaskProgressProps {
  /** 任务名称 */
  taskName: string;
  /** 当前阶段列表 */
  stages: TaskStage[];
  /** 总任务数 */
  totalCount: number;
  /** 成功数 */
  successCount: number;
  /** 失败数 */
  failureCount: number;
  /** 进度百分比 (0-100) */
  progressPercent?: number;
  /** 任务状态 */
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  /** 失败原因 */
  errorMessage?: string;
  /** 最近更新时间 */
  lastUpdatedAt?: string;
  /** 重试回调 */
  onRetry?: () => void;
  /** 是否显示进度条 */
  showProgressBar?: boolean;
}

/**
 * 任务进度组件
 * 用于文档处理、索引任务、评估任务等长任务的状态展示
 * 包含阶段步骤条、进度条、成功/失败统计和重试入口
 */
export function TaskProgress({
  taskName,
  stages,
  totalCount,
  successCount,
  failureCount,
  progressPercent,
  status,
  errorMessage,
  lastUpdatedAt,
  onRetry,
  showProgressBar = true,
}: TaskProgressProps) {
  /** 状态标签 */
  const statusTag = {
    pending: { color: 'default', icon: <ClockCircleOutlined />, text: '等待中' },
    running: { color: 'processing', icon: <SyncOutlined spin />, text: '运行中' },
    completed: { color: 'success', icon: <CheckCircleOutlined />, text: '已完成' },
    failed: { color: 'error', icon: <CloseCircleOutlined />, text: '失败' },
    cancelled: { color: 'default', icon: <ClockCircleOutlined />, text: '已取消' },
  }[status];

  return (
    <div style={{ padding: '16px 0' }}>
      {/* 任务名称和状态 */}
      <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
        <Space>
          <Text strong>{taskName}</Text>
          <Tag color={statusTag.color} icon={statusTag.icon}>
            {statusTag.text}
          </Tag>
        </Space>
        {onRetry && status === 'failed' && (
          <Tooltip title="重新执行">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={onRetry}
              type="link"
            >
              重试
            </Button>
          </Tooltip>
        )}
      </Space>

      {/* 阶段步骤条 */}
      {stages.length > 0 && (
        <Steps
          size="small"
          current={stages.findIndex((s) => s.status === 'process')}
          status={status === 'failed' ? 'error' : 'process'}
          items={stages.map((stage) => ({
            title: stage.name,
            description: stage.description,
            status: stage.status,
          }))}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 进度条 */}
      {showProgressBar && progressPercent !== undefined && (
        <Progress
          percent={progressPercent}
          status={status === 'failed' ? 'exception' : status === 'completed' ? 'success' : 'active'}
          style={{ marginBottom: 12 }}
        />
      )}

      {/* 统计信息 */}
      <Space size="large" style={{ marginBottom: 8 }}>
        <Text type="secondary">
          总任务数：<Text strong>{totalCount}</Text>
        </Text>
        <Text type="secondary">
          成功：<Text strong style={{ color: '#52c41a' }}>{successCount}</Text>
        </Text>
        <Text type="secondary">
          失败：<Text strong style={{ color: '#ff4d4f' }}>{failureCount}</Text>
        </Text>
      </Space>

      {/* 失败原因 */}
      {errorMessage && status === 'failed' && (
        <div style={{ marginTop: 8 }}>
          <Text type="danger">失败原因：{errorMessage}</Text>
        </div>
      )}

      {/* 最近更新时间 */}
      {lastUpdatedAt && (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            最近更新：{lastUpdatedAt}
          </Text>
        </div>
      )}
    </div>
  );
}