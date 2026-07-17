/**
 * 管理后台 - 操作日志页面
 * 成员3：管理后台前端 - 4.8 安全与审计
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Tag } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { DataTable, FilterBar, DetailDrawer } from '@/components/admin';
import { usePagination, useDetailDrawer } from '@/hooks/admin';
import type { OperationLog } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

const ACTION_MAP: Record<string, { label: string; color: string }> = {
  create: { label: '创建', color: 'green' }, update: { label: '更新', color: 'blue' },
  delete: { label: '删除', color: 'red' }, view: { label: '查看', color: 'default' },
  login: { label: '登录', color: 'cyan' }, logout: { label: '登出', color: 'default' },
  publish: { label: '发布', color: 'purple' }, unpublish: { label: '下线', color: 'orange' },
  approve: { label: '审核通过', color: 'green' }, reject: { label: '驳回', color: 'red' },
};

export function OperationLogs() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: drawerOpen, data: selectedLog, show: showDetail, hide: hideDetail } = useDetailDrawer<OperationLog>();
  const [logs, setLogs] = useState<OperationLog[]>([]);
  const [loading, setLoading] = useState(false);

  const mockLogs: OperationLog[] = [
    { id: 'log_001', user_id: 'usr_001', user_name: '系统管理员', action: 'create', resource_type: 'user', resource_id: 'usr_006', resource_name: '新用户', ip_address: '192.168.1.1', status_code: 200, duration_ms: 45, trace_id: 'trace_001', created_at: '2026-07-16 09:00:00' },
    { id: 'log_002', user_id: 'usr_001', user_name: '系统管理员', action: 'update', resource_type: 'role', resource_id: 'role_002', resource_name: '知识库管理员', ip_address: '192.168.1.1', status_code: 200, duration_ms: 32, trace_id: 'trace_002', created_at: '2026-07-16 09:05:00' },
    { id: 'log_003', user_id: 'usr_002', user_name: '张三', action: 'delete', resource_type: 'document', resource_id: 'doc_010', resource_name: '旧版本文档.pdf', ip_address: '192.168.1.50', status_code: 200, duration_ms: 120, trace_id: 'trace_003', created_at: '2026-07-16 09:10:00' },
    { id: 'log_004', user_id: 'usr_001', user_name: '系统管理员', action: 'publish', resource_type: 'qa', resource_id: 'qa_001', resource_name: '如何重置密码', ip_address: '192.168.1.1', status_code: 200, duration_ms: 56, trace_id: 'trace_004', created_at: '2026-07-16 09:15:00' },
    { id: 'log_005', user_id: 'usr_003', user_name: '李四', action: 'view', resource_type: 'document', resource_id: 'doc_001', resource_name: '系统架构设计文档.pdf', ip_address: '192.168.1.100', status_code: 403, duration_ms: 15, trace_id: 'trace_005', created_at: '2026-07-16 09:20:00' },
    { id: 'log_006', user_id: 'usr_001', user_name: '系统管理员', action: 'login', resource_type: 'auth', resource_id: 'usr_001', ip_address: '192.168.1.1', status_code: 200, duration_ms: 234, trace_id: 'trace_006', created_at: '2026-07-16 08:00:00' },
    { id: 'log_007', user_id: 'usr_002', user_name: '张三', action: 'update', resource_type: 'knowledge_base', resource_id: 'kb_001', resource_name: '技术文档库', ip_address: '192.168.1.50', status_code: 200, duration_ms: 67, trace_id: 'trace_007', created_at: '2026-07-16 09:30:00' },
    { id: 'log_008', user_id: 'usr_001', user_name: '系统管理员', action: 'reject', resource_type: 'qa', resource_id: 'qa_002', resource_name: 'Nginx SSL配置', ip_address: '192.168.1.1', status_code: 200, duration_ms: 89, trace_id: 'trace_008', created_at: '2026-07-16 09:35:00' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setLogs(mockLogs); setLoading(false); }, 300);
  }, []);

  const columns: ColumnsType<OperationLog> = [
    { title: '用户', dataIndex: 'user_name', key: 'user_name', width: 120 },
    { title: '操作', dataIndex: 'action', key: 'action', width: 100, render: (a: string) => { const cfg = ACTION_MAP[a] || { label: a, color: 'default' }; return <Tag color={cfg.color}>{cfg.label}</Tag>; }},
    { title: '资源', dataIndex: 'resource_name', key: 'resource_name', width: 180, ellipsis: true, render: (t: string) => t || <Text type="secondary">-</Text> },
    { title: '类型', dataIndex: 'resource_type', key: 'resource_type', width: 100 },
    { title: 'IP', dataIndex: 'ip_address', key: 'ip_address', width: 140 },
    { title: '状态', dataIndex: 'status_code', key: 'status_code', width: 80, render: (c: number) => <Tag color={c >= 400 ? 'red' : 'green'}>{c}</Tag> },
    { title: '耗时', dataIndex: 'duration_ms', key: 'duration_ms', width: 80, render: (ms: number) => `${ms}ms` },
    { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
    { title: '操作', key: 'action_col', width: 80, fixed: 'right', render: (_: unknown, r: OperationLog) => <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(r)}>详情</Button> },
  ];

  return (
    <div>
      <div className={styles.pageHeader}><Title level={3} className={styles.pageTitle}>操作日志</Title><Text type="secondary">记录管理员所有操作行为，支持按用户、时间、操作类型筛选</Text></div>
      <FilterBar filters={[
        { key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '用户/资源名称' },
        { key: 'action', label: '操作', type: 'select' as const, options: [{ label: '创建', value: 'create' }, { label: '更新', value: 'update' }, { label: '删除', value: 'delete' }, { label: '发布', value: 'publish' }, { label: '审核', value: 'approve' }] },
      ]} values={filters} onChange={handleFilterChange} onSearch={handleSearch} onReset={handleReset} />
      <DataTable<OperationLog> columns={columns} dataSource={logs} rowKey="id" page={pagination.page} pageSize={pagination.page_size} total={logs.length} loading={loading} onChange={(p, ps) => handlePageChange(p, ps)} emptyDescription="暂无操作日志" />
      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="日志详情" width={480}
        items={selectedLog ? [
          { key: 'user_name', label: '用户', children: selectedLog.user_name },
          { key: 'action', label: '操作', children: <Tag color={ACTION_MAP[selectedLog.action]?.color}>{ACTION_MAP[selectedLog.action]?.label || selectedLog.action}</Tag> },
          { key: 'resource_type', label: '资源类型', children: selectedLog.resource_type },
          { key: 'resource_name', label: '资源名称', children: selectedLog.resource_name || '-' },
          { key: 'resource_id', label: '资源ID', children: <Text code>{selectedLog.resource_id}</Text> },
          { key: 'ip_address', label: 'IP地址', children: selectedLog.ip_address },
          { key: 'status_code', label: '状态码', children: <Tag color={selectedLog.status_code >= 400 ? 'red' : 'green'}>{selectedLog.status_code}</Tag> },
          { key: 'duration_ms', label: '耗时', children: `${selectedLog.duration_ms}ms` },
          { key: 'trace_id', label: 'Trace ID', children: <Text code>{selectedLog.trace_id}</Text> },
          { key: 'created_at', label: '时间', children: selectedLog.created_at },
        ] : []}
        footerActions={<Space><Button onClick={hideDetail}>关闭</Button></Space>} />
    </div>
  );
}