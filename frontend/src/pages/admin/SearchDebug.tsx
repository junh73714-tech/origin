/**
 * 管理后台 - 检索调试页面
 * 成员3：管理后台前端 - 4.6 检索调试
 */
import { useState } from 'react';
import { Typography, Input, Button, Select, Card, Space, Divider, Table, Tag, Collapse, Descriptions, Switch, Row, Col } from 'antd';
import { SearchOutlined, ClockCircleOutlined } from '@ant-design/icons';
import type { SearchDebugResult, SearchResultItem } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text, Paragraph } = Typography;
const { Panel } = Collapse;

export function SearchDebug() {
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SearchDebugResult | null>(null);
  const [selectedKB, setSelectedKB] = useState<string[]>([]);
  const [rerankerEnabled, setRerankerEnabled] = useState(true);

  const handleSearch = () => {
    if (!question.trim()) return;
    setLoading(true);
    setTimeout(() => {
      setResult({
        request_id: 'req_debug_001',
        original_question: question,
        rewritten_question: '如何配置 Nginx 反向代理？',
        intent: 'technical_question',
        keywords: ['Nginx', '反向代理', '配置'],
        entities: ['Nginx'],
        permission_filter: 'tenant_id = "tnt_001" AND kb_id IN ("kb_001", "kb_003")',
        matched_qa: { id: 'qa_001', question: 'Nginx反向代理如何配置？', answer: 'Nginx反向代理配置需要设置proxy_pass指令...', score: 0.92 },
        keyword_results: [
          { rank: 1, score: 0.85, document_id: 'doc_001', document_name: '运维手册.pdf', chunk_id: 'chk_001', chunk_content: 'Nginx反向代理配置示例，包括proxy_pass和upstream设置...', source: 'keyword' },
          { rank: 2, score: 0.72, document_id: 'doc_001', document_name: '运维手册.pdf', chunk_id: 'chk_002', chunk_content: '反向代理服务器的基本概念和工作原理...', source: 'keyword' },
        ],
        vector_results: [
          { rank: 1, score: 0.91, document_id: 'doc_001', document_name: '运维手册.pdf', chunk_id: 'chk_001', chunk_content: 'Nginx反向代理配置示例...', source: 'vector' },
          { rank: 2, score: 0.78, document_id: 'doc_003', document_name: '系统架构文档.pdf', chunk_id: 'chk_005', chunk_content: '使用Nginx作为反向代理实现负载均衡...', source: 'vector' },
        ],
        rrf_results: [
          { rank: 1, score: 0.88, document_id: 'doc_001', document_name: '运维手册.pdf', chunk_id: 'chk_001', chunk_content: 'Nginx反向代理配置示例...', source: 'rrf' },
          { rank: 2, score: 0.75, document_id: 'doc_001', document_name: '运维手册.pdf', chunk_id: 'chk_002', chunk_content: '反向代理服务器的基本概念...', source: 'rrf' },
          { rank: 3, score: 0.68, document_id: 'doc_003', document_name: '系统架构文档.pdf', chunk_id: 'chk_005', chunk_content: '使用Nginx作为反向代理...', source: 'rrf' },
        ],
        reranker_results: [
          { rank: 1, score: 0.95, document_id: 'doc_001', document_name: '运维手册.pdf', chunk_id: 'chk_001', chunk_content: 'Nginx反向代理配置示例...', source: 'reranker' },
          { rank: 2, score: 0.82, document_id: 'doc_003', document_name: '系统架构文档.pdf', chunk_id: 'chk_005', chunk_content: '使用Nginx作为反向代理...', source: 'reranker' },
        ],
        final_context: '基于检索结果，最相关的文档片段来自运维手册中的Nginx配置章节...',
        evidence_coverage: 0.85,
        final_answer: '要配置Nginx反向代理，需要在nginx.conf中设置proxy_pass指令，指向后端服务器地址。例如：proxy_pass http://backend; ...',
        references: [
          { document_id: 'doc_001', document_name: '运维手册.pdf', chunk_id: 'chk_001', chunk_content: 'Nginx反向代理配置示例...', relevance_score: 0.95 },
          { document_id: 'doc_003', document_name: '系统架构文档.pdf', chunk_id: 'chk_005', chunk_content: '使用Nginx作为反向代理...', relevance_score: 0.82 },
        ],
        stage_timing: [
          { stage: '意图识别', duration_ms: 45 }, { stage: '标准问答匹配', duration_ms: 12 },
          { stage: 'Keyword检索', duration_ms: 78 }, { stage: 'Vector检索', duration_ms: 156 },
          { stage: 'RRF融合', duration_ms: 8 }, { stage: 'Reranker重排', duration_ms: 234 },
          { stage: 'LLM生成', duration_ms: 1850 }, { stage: '总计', duration_ms: 2383 },
        ],
      });
      setLoading(false);
    }, 1500);
  };

  const searchResultColumns: ColumnsType<SearchResultItem> = [
    { title: '排名', dataIndex: 'rank', key: 'rank', width: 60 },
    { title: '文档', dataIndex: 'document_name', key: 'document_name', width: 150 },
    { title: 'Chunk内容', dataIndex: 'chunk_content', key: 'chunk_content', width: 300, ellipsis: true },
    { title: '分数', dataIndex: 'score', key: 'score', width: 80,
      render: (score: number) => <Text strong style={{ color: score > 0.8 ? '#52c41a' : '#fa8c16' }}>{score.toFixed(3)}</Text> },
    { title: '来源', dataIndex: 'source', key: 'source', width: 100,
      render: (source: string) => {
        const colorMap: Record<string, string> = { keyword: 'blue', vector: 'purple', rrf: 'cyan', reranker: 'green' };
        return <Tag color={colorMap[source] || 'default'}>{source}</Tag>;
      }},
  ];

  return (
    <div>
      <div className={styles.pageHeader}>
        <Title level={3} className={styles.pageTitle}>检索调试</Title>
        <Text type="secondary">输入测试问题，查看完整检索链路和结果，分析各阶段耗时</Text>
      </div>
      <Card style={{ marginBottom: 20 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Input.TextArea value={question} onChange={(e) => setQuestion(e.target.value)}
              placeholder="输入测试问题，例如：如何配置Nginx反向代理？" rows={2} style={{ fontSize: 14 }} />
          </Col>
        </Row>
        <Row gutter={16} style={{ marginTop: 12 }} align="middle">
          <Col span={6}>
            <Select mode="multiple" placeholder="选择知识库范围（可选）" value={selectedKB}
              onChange={setSelectedKB} options={[
                { label: '技术文档库', value: 'kb_001' }, { label: '产品知识库', value: 'kb_002' }, { label: '运维手册', value: 'kb_003' },
              ]} style={{ width: '100%' }} allowClear />
          </Col>
          <Col span={3}>
            <Space><Text type="secondary">Reranker</Text>
              <Switch checked={rerankerEnabled} onChange={setRerankerEnabled} /></Space>
          </Col>
          <Col><Button type="primary" icon={<SearchOutlined />} loading={loading} onClick={handleSearch} size="large">执行检索</Button></Col>
        </Row>
      </Card>
      {result && (
        <div>
          <Card title="基本信息" style={{ marginBottom: 16 }}>
            <Descriptions column={2} size="small">
              <Descriptions.Item label="原始问题">{result.original_question}</Descriptions.Item>
              <Descriptions.Item label="改写问题">{result.rewritten_question || '-'}</Descriptions.Item>
              <Descriptions.Item label="意图">{result.intent || '-'}</Descriptions.Item>
              <Descriptions.Item label="关键词">{result.keywords.join(', ')}</Descriptions.Item>
              <Descriptions.Item label="实体">{result.entities.join(', ') || '-'}</Descriptions.Item>
              <Descriptions.Item label="证据覆盖度">{`${(result.evidence_coverage * 100).toFixed(1)}%`}</Descriptions.Item>
              <Descriptions.Item label="权限过滤条件" span={2}><Text code>{result.permission_filter}</Text></Descriptions.Item>
            </Descriptions>
          </Card>
          {result.matched_qa && (
            <Card title="标准问答匹配" size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="匹配问题">{result.matched_qa.question}</Descriptions.Item>
                <Descriptions.Item label="匹配答案">{result.matched_qa.answer}</Descriptions.Item>
                <Descriptions.Item label="匹配分数"><Text strong style={{ color: '#52c41a' }}>{(result.matched_qa.score * 100).toFixed(1)}%</Text></Descriptions.Item>
              </Descriptions>
            </Card>
          )}
          <Collapse defaultActiveKey={['reranker']} style={{ marginBottom: 16 }}>
            <Panel header={`Keyword 检索结果 (${result.keyword_results.length}条)`} key="keyword">
              <Table columns={searchResultColumns} dataSource={result.keyword_results} rowKey="rank" size="small" pagination={false} />
            </Panel>
            <Panel header={`Vector 检索结果 (${result.vector_results.length}条)`} key="vector">
              <Table columns={searchResultColumns} dataSource={result.vector_results} rowKey="rank" size="small" pagination={false} />
            </Panel>
            <Panel header={`RRF 融合结果 (${result.rrf_results.length}条)`} key="rrf">
              <Table columns={searchResultColumns} dataSource={result.rrf_results} rowKey="rank" size="small" pagination={false} />
            </Panel>
            <Panel header={`Reranker 重排结果 (${result.reranker_results.length}条)`} key="reranker">
              <Table columns={searchResultColumns} dataSource={result.reranker_results} rowKey="rank" size="small" pagination={false} />
            </Panel>
          </Collapse>
          <Card title="最终答案" style={{ marginBottom: 16 }}>
            <Paragraph>{result.final_answer}</Paragraph>
            <Divider /><Text strong>引用来源：</Text>
            {result.references.map((ref, idx) => (
              <div key={idx} style={{ marginTop: 8, padding: 8, background: '#fafafa', borderRadius: 4 }}>
                <Space><Tag>{ref.document_name}</Tag><Text type="secondary">相关度: {(ref.relevance_score * 100).toFixed(0)}%</Text></Space>
                <Paragraph style={{ marginTop: 4, fontSize: 13 }} ellipsis={{ rows: 2 }}>{ref.chunk_content}</Paragraph>
              </div>
            ))}
          </Card>
          <Card title={<Space><ClockCircleOutlined />各阶段耗时</Space>}>
            <Row gutter={[16, 8]}>
              {result.stage_timing.map((stage, idx) => (
                <Col span={6} key={idx}>
                  <div style={{ padding: '8px 12px', background: '#fafafa', borderRadius: 6, textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>{stage.stage}</Text><br />
                    <Text strong style={{ fontSize: 18, color: stage.stage === '总计' ? '#1677ff' : '#1f1f1f' }}>{stage.duration_ms}ms</Text>
                  </div>
                </Col>
              ))}
            </Row>
          </Card>
        </div>
      )}
    </div>
  );
}