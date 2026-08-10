/**
 * 管理后台 - 安全事件页面
 * 成员3：管理后台前端 - 4.8 安全与审计
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, message, Tag, Descriptions } from 'antd';
import { EyeOutlined, CheckCircleOutlined, WarningOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { DataTable, FilterBar, StatusTag, DetailDrawer } from '@/components/admin';
import { usePagination, useDetailDrawer } from '@/hooks/admin';
import type { SecurityEvent, SecurityEventSeverity } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

const SEVERITY_COLOR: Record<SecurityEventSeverity, string> = { low: 'blue', medium: 'orange', high: 'red', critical: 'red' };

const EVENT_TYPE_MAP: Record<string, string> = {
  unauthorized_access: '越权访问', prompt_injection: '提示词注入', brute_force: '暴力破解',
  abnormal_login: '异常登录', data_leak: '数据泄露', permission_escalation: '权限提升',
};

export function SecurityEvents() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: drawerOpen, data: selectedEvent, show: showDetail, hide: hideDetail } = useDetailDrawer<SecurityEvent>();
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(false);

  const mockEvents: SecurityEvent[] = [
    { id: 'sec_001', event_type: 'prompt_injection', severity: 'high', user_id: 'usr_003', user_name: '李四', ip_address: '192.168.1.100', description: '检测到用户尝试注入系统提示词，已在问题中检测到恶意指令模式', detail: { pattern: 'ignore previous instructions', matched_at: '2026-07-15 10:23' }, resolved: false, created_at: '2026-07-15 10:23' },
    { id: 'sec_002', event_type: 'unauthorized_access', severity: 'medium', user_id: 'usr_005', user_name: '赵六', ip_address: '10.0.0.55', description: '用户尝试访问无权限的知识库，连续3次被拒绝', detail: { target_kb: 'kb_003', attempt_count: 3 }, resolved: true, resolved_at: '2026-07-15 14:00', created_at: '2026-07-15 13:45' },
    { id: 'sec_003', event_type: 'abnormal_login', severity: 'low', user_id: 'usr_002', user_name: '张三', ip_address: '203.0.113.42', description: '从异常地理位置登录，IP地址与常用地址不一致', detail: { location: '未知城市', usual_location: '北京' }, resolved: false, created_at: '2026-07-16 02:15' },
    { id: 'sec_004', event_type: 'brute_force', severity: 'critical', user_id: undefined, ip_address: '198.51.100.23', description: '检测到针对admin账户的暴力破解攻击，1分钟内尝试登录超过50次', detail: { target_user: 'admin', attempt_count: 58, duration_seconds: 60 }, resolved: false, created_at: '2026-07-16 05:00' },
    { id: 'sec_005', event_type: 'data_leak', severity: 'high', user_id: 'usr_001', user_name: '系统管理员', ip_address: '192.168.1.1', description: '检测到大量文档下载行为，单次下载超过100份文档', detail: { document_count: 120, kb_id: 'kb_001' }, resolved: false, created_at: '2026-07-16 08:30' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setEvents(mockEvents); setLoading(false); }, 300);
  }, []);

  const columns: ColumnsType<SecurityEvent> = [
    { title: '事件类型', dataIndex: 'event_type', key: 'event_type', width: 140,
      render: (t: string) => <Tag>{EVENT_TYPE_MAP[t] || t}</Tag> },
    { title: '严重级别', dataIndex: 'severity', key: 'severity', width: 100,
      render: (s: SecurityEventSeverity) => <Tag color={SEVERITY_COLOR[s]}>{s === 'critical' ? '严重' : s === 'high' ? '高' : s === 'medium' ? '中' : '低'}</Tag> },
    { title: '用户', dataIndex: 'user_name', key: 'user_name', width: 120, render: (t: string) => t || <Text type="secondary">匿名</Text> },
    { title: 'IP地址', dataIndex: 'ip_address', key: 'ip_address', width: 140 },
    { title: '描述', dataIndex: 'description', key: 'description', width: 280, ellipsis: true },
    { title: '处理状态', dataIndex: 'resolved', key: 'resolved', width: 100,
      render: (resolved: boolean) => resolved ? <Tag color="green" icon={<CheckCircleOutlined />}>已处理</Tag> : <Tag color="red" icon={<WarningOutlined />}>未处理</Tag> },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 140 },
    { title: '操作', key: 'action', width: 120, fixed: 'right',
      render: (_: unknown, r: SecurityEvent) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(r)}>详情</Button>
          {!r.resolved && <Button type="link" size="small" icon={<CheckCircleOutlined />} onClick={() => message.success('已标记为已处理')}>处理</Button>}
        </Space>
      )},
  ];

  return (
    <div>
      <div className={styles.pageHeader}><Title level={3} className={styles.pageTitle}>安全事件</Title><Text type="secondary">监控系统安全事件，包括越权访问、注入攻击、异常登录等</Text></div>
      <FilterBar filters={[
        { key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '描述关键词' },
        { key: 'severity', label: '级别', type: 'select' as const, options: [{ label: '严重', value: 'critical' }, { label: '高', value: 'high' }, { label: '中', value: 'medium' }, { label: '低', value: 'low' }] },
        { key: 'resolved', label: '状态', type: 'select' as const, options: [{ label: '未处理', value: 'false' }, { label: '已处理', value: 'true' }] },
      ]} values={filters} onChange={handleFilterChange} onSearch={handleSearch} onReset={handleReset} />
      <DataTable<SecurityEvent> columns={columns} dataSource={events} rowKey="id" page={pagination.page} pageSize={pagination.page_size} total={events.length} loading={loading} onChange={(p, ps) => handlePageChange(p, ps)} emptyDescription="暂无安全事件" />
      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="安全事件详情" width={560}
        items={selectedEvent ? [
          { key: 'event_type', label: '事件类型', children: <Tag>{EVENT_TYPE_MAP[selectedEvent.event_type] || selectedEvent.event_type}</Tag> },
          { key: 'severity', label: '严重级别', children: <Tag color={SEVERITY_COLOR[selectedEvent.severity]}>{selectedEvent.severity}</Tag> },
          { key: 'user_name', label: '用户', children: selectedEvent.user_name || '匿名' },
          { key: 'ip_address', label: 'IP地址', children: selectedEvent.ip_address },
          { key: 'description', label: '描述', children: selectedEvent.description },
          { key: 'resolved', label: '处理状态', children: selectedEvent.resolved ? <Tag color="green">已处理</Tag> : <Tag color="red">未处理</Tag> },
          { key: 'created_at', label: '发生时间', children: selectedEvent.created_at },
          { key: 'resolved_at', label: '处理时间', children: selectedEvent.resolved_at || '-' },
        ] : []}
        extra={selectedEvent?.detail && (
          <div style={{ marginTop: 16 }}>
            <Text strong>详细信息：</Text>
            <pre style={{ marginTop: 8, padding: 12, background: '#fafafa', borderRadius: 6, fontSize: 13, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(selectedEvent.detail, null, 2)}
            </pre>
          </div>
        )}
        footerActions={<Space><Button onClick={hideDetail}>关闭</Button>
          {selectedEvent && !selectedEvent.resolved && <Button type="primary" onClick={() => { message.success('已标记为已处理'); hideDetail(); }}>标记为已处理</Button>}
        </Space>}
      />
    </div>
  );
}