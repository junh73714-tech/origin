/**
 * 管理后台 - 索引任务管理页面
 * 成员3：管理后台前端 - 4.4 知识库和文档
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, message, Progress } from 'antd';
import { ReloadOutlined, EyeOutlined } from '@ant-design/icons';
import { DataTable, FilterBar, StatusTag, TaskProgress, DetailDrawer } from '@/components/admin';
import { usePagination, useDetailDrawer } from '@/hooks/admin';
import type { IndexTask, TaskStage } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

export function IndexTaskManagement() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: drawerOpen, data: selectedTask, show: showDetail, hide: hideDetail } = useDetailDrawer<IndexTask>();
  const [tasks, setTasks] = useState<IndexTask[]>([]);
  const [loading, setLoading] = useState(false);

  const mockTasks: IndexTask[] = [
    { id: 'task_001', document_id: 'doc_001', document_name: '系统架构设计文档.pdf', task_type: 'both', status: 'completed', progress: 100, total_chunks: 45, indexed_chunks: 45, failed_chunks: 0, started_at: '2026-07-15 08:00', completed_at: '2026-07-15 08:05', updated_at: '2026-07-15 08:05' },
    { id: 'task_002', document_id: 'doc_003', document_name: '产品需求文档.pdf', task_type: 'both', status: 'running', progress: 65, total_chunks: 68, indexed_chunks: 44, failed_chunks: 2, error_message: '2个Chunk向量化超时', started_at: '2026-07-15 10:00', updated_at: '2026-07-15 10:12' },
    { id: 'task_003', document_id: 'doc_004', document_name: '用户手册.docx', task_type: 'vector', status: 'running', progress: 30, total_chunks: 32, indexed_chunks: 10, failed_chunks: 0, started_at: '2026-07-15 11:00', updated_at: '2026-07-15 11:08' },
    { id: 'task_004', document_id: 'doc_005', document_name: '部署运维手册.pdf', task_type: 'both', status: 'failed', progress: 42, total_chunks: 28, indexed_chunks: 12, failed_chunks: 16, error_message: 'OpenSearch连接超时', started_at: '2026-07-14 14:00', updated_at: '2026-07-14 14:15' },
    { id: 'task_005', document_id: 'doc_006', document_name: '监控配置指南.xlsx', task_type: 'keyword', status: 'completed', progress: 100, total_chunks: 12, indexed_chunks: 12, failed_chunks: 0, started_at: '2026-07-13 09:00', completed_at: '2026-07-13 09:02', updated_at: '2026-07-13 09:02' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setTasks(mockTasks); setLoading(false); }, 300);
  }, []);

  const getStages = (task: IndexTask): TaskStage[] => {
    const stages: TaskStage[] = [
      { name: '文档解析', status: 'finish', description: '完成' },
      { name: 'Chunk切分', status: 'finish', description: `${task.total_chunks}个Chunk` },
    ];
    if (task.task_type === 'keyword' || task.task_type === 'both') {
      stages.push({ name: 'Keyword索引', status: task.status === 'running' ? 'process' : task.status === 'completed' ? 'finish' : 'error' });
    }
    if (task.task_type === 'vector' || task.task_type === 'both') {
      stages.push({ name: 'Vector索引', status: task.status === 'running' ? 'process' : task.status === 'completed' ? 'finish' : 'error' });
    }
    return stages;
  };

  const columns: ColumnsType<IndexTask> = [
    { title: '文档名称', dataIndex: 'document_name', key: 'document_name', width: 200,
      render: (text: string, record: IndexTask) => <a onClick={() => showDetail(record)}>{text}</a> },
    { title: '任务类型', dataIndex: 'task_type', key: 'task_type', width: 120,
      render: (type: string) => type === 'both' ? 'Keyword+Vector' : type === 'keyword' ? 'Keyword' : 'Vector' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (status: string) => <StatusTag status={status} /> },
    { title: '进度', dataIndex: 'progress', key: 'progress', width: 150,
      render: (progress: number, record: IndexTask) => (
        <Progress percent={progress} size="small"
          status={record.status === 'failed' ? 'exception' : record.status === 'completed' ? 'success' : 'active'} />
      ) },
    { title: 'Chunks', key: 'chunks', width: 100,
      render: (_: unknown, record: IndexTask) => <Text>{record.indexed_chunks}/{record.total_chunks}</Text> },
    { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 140 },
    { title: '操作', key: 'action', width: 120, fixed: 'right',
      render: (_: unknown, record: IndexTask) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(record)}>详情</Button>
          {record.status === 'failed' && (
            <Button type="link" size="small" icon={<ReloadOutlined />}
              onClick={() => message.success('已提交重试请求')}>重试</Button>
          )}
        </Space>
      ),
    },
  ];

  const filterItems = [
    { key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '文档名称' },
    { key: 'status', label: '状态', type: 'select' as const,
      options: [{ label: '运行中', value: 'running' }, { label: '已完成', value: 'completed' }, { label: '失败', value: 'failed' }] },
    { key: 'task_type', label: '类型', type: 'select' as const,
      options: [{ label: 'Keyword+Vector', value: 'both' }, { label: 'Keyword', value: 'keyword' }, { label: 'Vector', value: 'vector' }] },
  ];

  return (
    <div>
      <div className={styles.pageHeader}>
        <div>
          <Title level={3} className={styles.pageTitle}>索引任务</Title>
          <Text type="secondary">管理文档索引任务，查看进度和失败原因，支持重试</Text>
        </div>
      </div>
      <FilterBar filters={filterItems} values={filters} onChange={handleFilterChange}
        onSearch={handleSearch} onReset={handleReset} />
      <DataTable<IndexTask> columns={columns} dataSource={tasks} rowKey="id"
        page={pagination.page} pageSize={pagination.page_size} total={tasks.length}
        loading={loading} onChange={(page, pageSize) => handlePageChange(page, pageSize)}
        emptyDescription="暂无索引任务" />
      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="任务详情" width={560}
        items={selectedTask ? [
          { key: 'document_name', label: '文档', children: selectedTask.document_name },
          { key: 'task_type', label: '任务类型', children: selectedTask.task_type === 'both' ? 'Keyword + Vector' : selectedTask.task_type },
          { key: 'status', label: '状态', children: <StatusTag status={selectedTask.status} /> },
          { key: 'started_at', label: '开始时间', children: selectedTask.started_at || '-' },
          { key: 'completed_at', label: '完成时间', children: selectedTask.completed_at || '-' },
        ] : []}
        extra={selectedTask && (
          <TaskProgress taskName={selectedTask.document_name} stages={getStages(selectedTask)}
            totalCount={selectedTask.total_chunks} successCount={selectedTask.indexed_chunks}
            failureCount={selectedTask.failed_chunks} progressPercent={selectedTask.progress}
            status={selectedTask.status} errorMessage={selectedTask.error_message}
            lastUpdatedAt={selectedTask.updated_at}
            onRetry={selectedTask.status === 'failed' ? () => message.success('已提交重试请求') : undefined} />
        )}
      />
    </div>
  );
}