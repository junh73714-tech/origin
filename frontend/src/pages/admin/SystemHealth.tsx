/**
 * 管理后台 - 系统健康页面
 * 成员3：管理后台前端 - 4.9 系统设置
 */
import { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Statistic, Progress, Button, Space, Tag } from 'antd';
import { CheckCircleOutlined, ExclamationCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import type { SystemHealth, ComponentHealth } from '@/types/admin';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

const STATUS_CFG: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
  healthy: { color: '#52c41a', icon: <CheckCircleOutlined />, text: '健康' },
  degraded: { color: '#fa8c16', icon: <ExclamationCircleOutlined />, text: '降级' },
  unhealthy: { color: '#ff4d4f', icon: <CloseCircleOutlined />, text: '异常' },
};

const MOCK_HEALTH: SystemHealth = {
  status: 'healthy',
  components: {
    postgresql: { status: 'healthy', latency_ms: 12 },
    redis: { status: 'healthy', latency_ms: 3 },
    opensearch: { status: 'healthy', latency_ms: 45 },
    minio: { status: 'healthy', latency_ms: 28 },
    celery: { status: 'degraded', latency_ms: 250, message: 'Worker队列积压，处理延迟增加' },
  },
  uptime_hours: 720.5, memory_usage_percent: 62.3, cpu_usage_percent: 34.7, disk_usage_percent: 45.1,
};

function HealthCard({ name, health }: { name: string; health: ComponentHealth }) {
  const cfg = STATUS_CFG[health.status];
  return (
    <Card size="small" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space><span style={{ color: cfg.color }}>{cfg.icon}</span><Text strong>{name}</Text><Tag color={cfg.color}>{cfg.text}</Tag></Space>
        <Space><Text type="secondary">延迟:</Text><Text strong style={{ color: health.latency_ms > 100 ? '#ff4d4f' : '#52c41a' }}>{health.latency_ms}ms</Text></Space>
      </div>
      {health.message && <Text type="warning" style={{ fontSize: 12, display: 'block', marginTop: 4 }}>{health.message}</Text>}
    </Card>
  );
}

export function SystemHealth() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(false);
  const loadHealth = () => { setLoading(true); setTimeout(() => { setHealth(MOCK_HEALTH); setLoading(false); }, 500); };
  useEffect(() => { loadHealth(); }, []);
  const overallCfg = health ? STATUS_CFG[health.status] : STATUS_CFG.healthy;

  return (
    <div>
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div><Title level={3} className={styles.pageTitle}>系统健康</Title><Text type="secondary">监控系统各组件的运行状态和资源使用情况</Text></div>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={loadHealth}>刷新状态</Button>
        </div>
      </div>
      {health && (
        <>
          <Card style={{ marginBottom: 20, textAlign: 'center' }}>
            <div style={{ color: overallCfg.color, fontSize: 48, marginBottom: 8 }}>{overallCfg.icon}</div>
            <Title level={4} style={{ color: overallCfg.color, margin: 0 }}>系统状态：{overallCfg.text}</Title>
            <Text type="secondary">运行时间：{health.uptime_hours.toFixed(1)} 小时</Text>
          </Card>
          <Row gutter={16} style={{ marginBottom: 20 }}>
            {[{ label: 'CPU使用率', value: health.cpu_usage_percent }, { label: '内存使用率', value: health.memory_usage_percent }, { label: '磁盘使用率', value: health.disk_usage_percent }].map((item, i) => (
              <Col span={8} key={i}>
                <Card><Statistic title={item.label} value={item.value} suffix="%" valueStyle={{ color: item.value > 80 ? '#ff4d4f' : '#52c41a' }} />
                  <Progress percent={item.value} showInfo={false} strokeColor={item.value > 80 ? '#ff4d4f' : '#1677ff'} /></Card>
              </Col>
            ))}
          </Row>
          <Card title="组件状态">
            <HealthCard name="PostgreSQL" health={health.components.postgresql} />
            <HealthCard name="Redis" health={health.components.redis} />
            <HealthCard name="OpenSearch" health={health.components.opensearch} />
            <HealthCard name="MinIO" health={health.components.minio} />
            <HealthCard name="Celery Worker" health={health.components.celery} />
          </Card>
        </>
      )}
    </div>
  );
}