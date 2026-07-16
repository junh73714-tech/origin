/**
 * 管理后台 - 待审核问答页面
 * 成员3：管理后台前端 - 4.5 问答优化
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Modal, Form, Input, message, Tag, Alert, Descriptions } from 'antd';
import { CheckOutlined, CloseOutlined, EditOutlined, EyeOutlined, FileTextOutlined } from '@ant-design/icons';
import { DataTable, FilterBar, StatusTag, DetailDrawer } from '@/components/admin';
import { usePagination, useDetailDrawer } from '@/hooks/admin';
import type { CandidateQA, ReviewAction } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text, Paragraph } = Typography;

export function PendingReview() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: drawerOpen, data: selectedQA, show: showDetail, hide: hideDetail } = useDetailDrawer<CandidateQA>();
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewAction, setReviewAction] = useState<ReviewAction>('approve');
  const [reviewComment, setReviewComment] = useState('');
  const [qas, setQAs] = useState<CandidateQA[]>([]);
  const [loading, setLoading] = useState(false);

  const mockQAs: CandidateQA[] = [
    { id: 'qa_001', question: '如何重置用户密码？', answer: '管理员可以在用户管理页面中，点击重置密码按钮来重置用户密码。', source_document_id: 'doc_002', source_document_name: '用户管理手册.pdf', source_chunk_id: 'chk_012', source_document_version: 2, knowledge_base_id: 'kb_001', knowledge_base_name: '技术文档库', status: 'pending', review_history: [], created_by: 'auto', created_at: '2026-07-15 10:00', updated_at: '2026-07-15 10:00' },
    { id: 'qa_002', question: 'Nginx反向代理如何配置SSL？', answer: '配置SSL需要在server块中指定ssl_certificate和ssl_certificate_key路径。', source_document_id: 'doc_001', source_document_name: '运维手册.pdf', source_chunk_id: 'chk_003', source_document_version: 3, knowledge_base_id: 'kb_001', knowledge_base_name: '技术文档库', status: 'pending', auto_quality_check: { score: 85, issues: [{ type: 'completeness', description: '缺少完整的配置示例', severity: 'warning' }], checked_at: '2026-07-15' }, review_history: [], created_by: 'auto', created_at: '2026-07-15 14:00', updated_at: '2026-07-15 14:00' },
    { id: 'qa_003', question: '数据库备份策略有哪些？', answer: '推荐使用全量备份+增量备份的组合策略。', source_document_id: 'doc_003', source_document_name: '运维手册.pdf', source_chunk_id: 'chk_008', source_document_version: 1, knowledge_base_id: 'kb_003', knowledge_base_name: '运维手册', status: 'pending', auto_quality_check: { score: 92, issues: [], checked_at: '2026-07-15' }, review_history: [], created_by: 'auto', created_at: '2026-07-15 16:00', updated_at: '2026-07-15 16:00' },
    { id: 'qa_004', question: '如何申请API密钥？', answer: '联系系统管理员在后台生成API密钥，密钥有效期为90天。', source_document_id: 'doc_002', source_document_name: 'API接口规范.docx', source_chunk_id: 'chk_015', source_document_version: 2, knowledge_base_id: 'kb_001', knowledge_base_name: '技术文档库', status: 'revised', review_history: [{ reviewer_id: 'usr_001', reviewer_name: '系统管理员', action: 'return_for_revision', comment: '需补充密钥权限范围', reviewed_at: '2026-07-14' }], created_by: 'auto', created_at: '2026-07-14', updated_at: '2026-07-14' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setQAs(mockQAs); setLoading(false); }, 300);
  }, []);

  const columns: ColumnsType<CandidateQA> = [
    { title: '问题', dataIndex: 'question', key: 'question', width: 300, ellipsis: true, render: (text: string, record: CandidateQA) => <a onClick={() => showDetail(record)}>{text}</a> },
    { title: '知识库', dataIndex: 'knowledge_base_name', key: 'knowledge_base_name', width: 120 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (status: string) => <StatusTag status={status} /> },
    { title: '质量', key: 'quality', width: 80, render: (_: unknown, record: CandidateQA) => { const score = record.auto_quality_check?.score; if (!score) return <Text type="secondary">-</Text>; return <Text strong style={{ color: score >= 80 ? '#52c41a' : '#fa8c16' }}>{score}分</Text>; }},
    { title: '来源', dataIndex: 'source_document_name', key: 'source_document_name', width: 150 },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 140 },
    { title: '操作', key: 'action', width: 220, fixed: 'right', render: (_: unknown) => (
      <Space size="small">
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(mockQAs[0])}>详情</Button>
        <Button type="link" size="small" icon={<CheckOutlined />} style={{ color: '#52c41a' }} onClick={() => { setReviewAction('approve'); setReviewComment(''); setReviewOpen(true); }}>通过</Button>
        <Button type="link" size="small" danger icon={<CloseOutlined />} onClick={() => { setReviewAction('reject'); setReviewComment(''); setReviewOpen(true); }}>驳回</Button>
      </Space>
    )},
  ];

  return (
    <div>
      <div className={styles.pageHeader}><Title level={3} className={styles.pageTitle}>待审核问答</Title><Text type="secondary">审核自动生成的候选问答，支持通过、驳回、返回修改</Text></div>
      <FilterBar filters={[{ key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '搜索问题' }]} values={filters} onChange={handleFilterChange} onSearch={handleSearch} onReset={handleReset} />
      <DataTable<CandidateQA> columns={columns} dataSource={qas} rowKey="id" page={pagination.page} pageSize={pagination.page_size} total={qas.length} loading={loading} onChange={(p, ps) => handlePageChange(p, ps)} emptyDescription="暂无待审核问答" />
      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="审核详情" width={640}
        items={selectedQA ? [
          { key: 'question', label: '问题', children: <Text strong>{selectedQA.question}</Text> },
          { key: 'answer', label: '答案', children: <Paragraph>{selectedQA.answer}</Paragraph> },
          { key: 'source', label: '来源文档', children: selectedQA.source_document_name || '-' },
          { key: 'kb', label: '知识库', children: selectedQA.knowledge_base_name },
          { key: 'status', label: '状态', children: <StatusTag status={selectedQA.status} /> },
        ] : []}
        extra={selectedQA && (
          <div style={{ marginTop: 16 }}>
            {selectedQA.auto_quality_check && selectedQA.auto_quality_check.issues.length > 0 && (
              <div style={{ marginBottom: 16 }}><Text strong>质量检查：</Text>
                {selectedQA.auto_quality_check.issues.map((issue, idx) => <Alert key={idx} type="warning" message={issue.type} description={issue.description} style={{ marginTop: 8 }} showIcon />)}
              </div>
            )}
            {selectedQA.review_history.length > 0 && (
              <div><Text strong>审核历史：</Text>
                {selectedQA.review_history.map((h, idx) => <div key={idx} style={{ padding: 8, marginTop: 8, background: '#fffbe6', borderRadius: 4 }}><Space><Tag>{h.action}</Tag><Text>{h.reviewer_name}</Text><Text type="secondary">{h.reviewed_at}</Text></Space>{h.comment && <Paragraph style={{ marginTop: 4, fontSize: 13 }}>{h.comment}</Paragraph>}</div>)}
              </div>
            )}
            <div style={{ marginTop: 16 }}><Space>
              <Button type="primary" icon={<CheckOutlined />} onClick={() => { setReviewAction('approve'); setReviewOpen(true); hideDetail(); }}>通过</Button>
              <Button icon={<EditOutlined />} onClick={() => { setReviewAction('return_for_revision'); setReviewOpen(true); hideDetail(); }}>返回修改</Button>
              <Button danger icon={<CloseOutlined />} onClick={() => { setReviewAction('reject'); setReviewOpen(true); hideDetail(); }}>驳回</Button>
            </Space></div>
          </div>
        )}
        footerActions={<Space><Button onClick={hideDetail}>关闭</Button></Space>} />
      <Modal title="审核确认" open={reviewOpen} onCancel={() => setReviewOpen(false)} onOk={() => { message.success('审核完成'); setReviewOpen(false); loadData(); }} width={480} destroyOnClose>
        <Tag color={reviewAction === 'approve' ? 'green' : reviewAction === 'reject' ? 'red' : 'blue'} style={{ marginBottom: 12 }}>
          {reviewAction === 'approve' ? '通过' : reviewAction === 'reject' ? '驳回' : '返回修改'}
        </Tag>
        <Form.Item label="审核意见"><Input.TextArea value={reviewComment} onChange={(e) => setReviewComment(e.target.value)} placeholder="请输入审核意见（可选）" rows={3} /></Form.Item>
      </Modal>
    </div>
  );
}