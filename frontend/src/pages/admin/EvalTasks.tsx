/**
 * 管理后台 - 评估任务页面
 * 成员3：管理后台前端 - 4.7 评估中心
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Modal, Form, Input, Select, message, Progress, Descriptions } from 'antd';
import { PlusOutlined, EyeOutlined, ReloadOutlined, ExperimentOutlined } from '@ant-design/icons';
import { DataTable, FilterBar, StatusTag, TaskProgress, DetailDrawer } from '@/components/admin';
import { usePagination, useDetailDrawer } from '@/hooks/admin';
import type { EvaluationTask, TaskStage } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

export function EvalTasks() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: drawerOpen, data: selectedTask, show: showDetail, hide: hideDetail } = useDetailDrawer<EvaluationTask>();
  const [createOpen, setCreateOpen] = useState(false);
  const [tasks, setTasks] = useState<EvaluationTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const mockTasks: EvaluationTask[] = [
    { id: 'eval_001', name: '基线评估-2026Q3', dataset_id: 'ds_001', dataset_name: 'Golden Dataset v1', task_type: 'batch', status: 'completed', progress: 100, total_samples: 200, completed_samples: 200, failed_samples: 0, params_config: { top_k: 10, reranker: true }, created_at: '2026-07-10 09:00', completed_at: '2026-07-10 09:30' },
    { id: 'eval_002', name: 'Reranker对比测试', dataset_id: 'ds_001', dataset_name: 'Golden Dataset v1', task_type: 'batch', status: 'running', progress: 65, total_samples: 200, completed_samples: 130, failed_samples: 3, params_config: { top_k: 10, reranker: false }, created_at: '2026-07-15 14:00' },
    { id: 'eval_003', name: '单问题测试-权限验证', dataset_id: 'ds_002', dataset_name: '权限测试集', task_type: 'single', status: 'completed', progress: 100, total_samples: 1, completed_samples: 1, failed_samples: 0, created_at: '2026-07-15 16:00', completed_at: '2026-07-15 16:01' },
    { id: 'eval_004', name: 'TopK参数优化', dataset_id: 'ds_001', dataset_name: 'Golden Dataset v1', task_type: 'batch', status: 'failed', progress: 45, total_samples: 200, completed_samples: 90, failed_samples: 110, created_at: '2026-07-14 10:00' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setTasks(mockTasks); setLoading(false); }, 300);
  }, []);

  const getStages = (task: EvaluationTask): TaskStage[] => [
    { name: '准备数据', status: 'finish' },
    { name: '执行检索', status: task.status === 'running' ? 'process' : 'finish' },
    { name: '计算指标', status: task.status === 'completed' ? 'finish' : task.status === 'running' ? 'wait' : 'error' },
    { name: '生成报告', status: task.status === 'completed' ? 'finish' : 'wait' },
  ];

  const columns: ColumnsType<EvaluationTask> = [
    { title: '任务名称', dataIndex: 'name', key: 'name', width: 200, render: (t: string, r: EvaluationTask) => <a onClick={() => showDetail(r)}>{t}</a> },
    { title: '数据集', dataIndex: 'dataset_name', key: 'dataset_name', width: 150 },
    { title: '类型', dataIndex: 'task_type', key: 'task_type', width: 80, render: (t: string) => t === 'batch' ? '批量' : '单题' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (s: string) => <StatusTag status={s} /> },
    { title: '进度', dataIndex: 'progress', key: 'progress', width: 150, render: (p: number, r: EvaluationTask) => <Progress percent={p} size="small" status={r.status === 'failed' ? 'exception' : r.status === 'completed' ? 'success' : 'active'} /> },
    { title: '样本', key: 'samples', width: 100, render: (_: unknown, r: EvaluationTask) => <Text>{r.completed_samples}/{r.total_samples}</Text> },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 140 },
    { title: '操作', key: 'action', width: 120, fixed: 'right', render: (_: unknown, r: EvaluationTask) => (
      <Space size="small">
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(r)}>详情</Button>
        {r.status === 'failed' && <Button type="link" size="small" icon={<ReloadOutlined />} onClick={() => message.success('已重新提交')}>重试</Button>}
      </Space>
    )},
  ];

  return (
    <div>
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div><Title level={3} className={styles.pageTitle}>评估任务</Title><Text type="secondary">管理检索效果评估任务，查看进度和结果</Text></div>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { form.resetFields(); setCreateOpen(true); }}>创建评估任务</Button>
        </div>
      </div>
      <FilterBar filters={[
        { key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '任务名称' },
        { key: 'status', label: '状态', type: 'select' as const, options: [{ label: '运行中', value: 'running' }, { label: '已完成', value: 'completed' }, { label: '失败', value: 'failed' }] },
      ]} values={filters} onChange={handleFilterChange} onSearch={handleSearch} onReset={handleReset} />
      <DataTable<EvaluationTask> columns={columns} dataSource={tasks} rowKey="id" page={pagination.page} pageSize={pagination.page_size} total={tasks.length} loading={loading} onChange={(p, ps) => handlePageChange(p, ps)} emptyDescription="暂无评估任务" emptyActionText="创建评估任务" onEmptyAction={() => { form.resetFields(); setCreateOpen(true); }} />
      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="评估任务详情" width={560}
        items={selectedTask ? [
          { key: 'name', label: '任务名称', children: selectedTask.name },
          { key: 'dataset_name', label: '数据集', children: selectedTask.dataset_name },
          { key: 'status', label: '状态', children: <StatusTag status={selectedTask.status} /> },
          { key: 'progress', label: '进度', children: `${selectedTask.progress}%` },
          { key: 'created_at', label: '创建时间', children: selectedTask.created_at },
          { key: 'completed_at', label: '完成时间', children: selectedTask.completed_at || '-' },
        ] : []}
        extra={selectedTask && (
          <div style={{ marginTop: 16 }}>
            <TaskProgress taskName={selectedTask.name} stages={getStages(selectedTask)}
              totalCount={selectedTask.total_samples} successCount={selectedTask.completed_samples}
              failureCount={selectedTask.failed_samples} progressPercent={selectedTask.progress}
              status={selectedTask.status} lastUpdatedAt={selectedTask.completed_at || selectedTask.created_at}
              onRetry={selectedTask.status === 'failed' ? () => message.success('已提交重试') : undefined} />
            {selectedTask.results && (
              <div style={{ marginTop: 16 }}>
                <Text strong>评估结果：</Text>
                <Descriptions column={2} size="small" style={{ marginTop: 8 }}>
                  <Descriptions.Item label="MRR">{(selectedTask.results.retrieval_metrics.mrr * 100).toFixed(1)}%</Descriptions.Item>
                  <Descriptions.Item label="NDCG">{(selectedTask.results.retrieval_metrics.ndcg * 100).toFixed(1)}%</Descriptions.Item>
                  <Descriptions.Item label="BLEU">{(selectedTask.results.generation_metrics.bleu * 100).toFixed(1)}%</Descriptions.Item>
                  <Descriptions.Item label="Faithfulness">{(selectedTask.results.generation_metrics.faithfulness * 100).toFixed(1)}%</Descriptions.Item>
                </Descriptions>
              </div>
            )}
          </div>
        )}
      />
      <Modal title="创建评估任务" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={() => { message.success('评估任务已创建'); setCreateOpen(false); loadData(); }} width={480} destroyOnClose>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="任务名称" rules={[{ required: true }]}><Input placeholder="请输入任务名称" /></Form.Item>
          <Form.Item name="dataset_id" label="数据集" rules={[{ required: true }]}>
            <Select placeholder="请选择数据集" options={[{ label: 'Golden Dataset v1', value: 'ds_001' }, { label: '权限测试集', value: 'ds_002' }]} />
          </Form.Item>
          <Form.Item name="task_type" label="任务类型" initialValue="batch">
            <Select options={[{ label: '批量评估', value: 'batch' }, { label: '单题评估', value: 'single' }]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}