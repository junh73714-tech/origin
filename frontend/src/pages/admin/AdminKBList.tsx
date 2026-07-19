/**
 * 管理后台 - 知识库管理页面
 * 成员3：管理后台前端 - 4.4 知识库和文档
 * 知识库列表、创建、编辑、删除、授权 - 卡片网格布局
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Modal, Form, Input, Switch, message, Card, Tooltip } from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, DatabaseOutlined,
  FileTextOutlined, UserOutlined, SettingOutlined,
} from '@ant-design/icons';
import { StatusTag, ConfirmAction } from '@/components/admin';
import { useConfirmAction } from '@/hooks/admin';
import type { KnowledgeBase } from '@/api/knowledgeBase';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

/** 图标映射 */
const ICON_MAP: Record<string, React.ReactNode> = {
  database: <DatabaseOutlined />,
  file: <FileTextOutlined />,
  user: <UserOutlined />,
  setting: <SettingOutlined />,
};

/**
 * 知识库管理页面
 */
export function AdminKBList() {
  const { open: confirmOpen, confirmLoading, show: showConfirm, hide: hideConfirm } = useConfirmAction();
  const [editOpen, setEditOpen] = useState(false);
  const [editKB, setEditKB] = useState<KnowledgeBase | null>(null);
  const [kbs, setKBs] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  // 模拟数据
  const mockKBs: KnowledgeBase[] = [
    { id: 'kb_001', name: '技术文档库', description: '公司技术架构、API文档、开发规范', icon: 'database', is_public: false, document_count: 156, created_at: '2026-01-15', updated_at: '2026-07-15' },
    { id: 'kb_002', name: '产品知识库', description: '产品需求文档、设计规范、用户手册', icon: 'file', is_public: true, document_count: 89, created_at: '2026-02-20', updated_at: '2026-07-14' },
    { id: 'kb_003', name: '运维手册', description: '部署文档、故障排查、监控配置', icon: 'setting', is_public: false, document_count: 45, created_at: '2026-03-10', updated_at: '2026-07-13' },
    { id: 'kb_004', name: '人力资源知识库', description: '员工手册、培训资料、规章制度', icon: 'user', is_public: false, document_count: 32, created_at: '2026-04-01', updated_at: '2026-07-12' },
    { id: 'kb_005', name: '客户FAQ', description: '常见问题解答、产品使用指南', icon: 'file', is_public: true, document_count: 78, created_at: '2026-05-15', updated_at: '2026-07-11' },
    { id: 'kb_006', name: '法律法规库', description: '行业法规、合规文档、政策文件', icon: 'file', is_public: false, document_count: 23, created_at: '2026-06-01', updated_at: '2026-07-10' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setKBs(mockKBs); setLoading(false); }, 300);
  }, []);

  return (
    <div>
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={3} className={styles.pageTitle}>知识库管理</Title>
            <Text type="secondary">管理知识库，包括创建、编辑、删除和授权操作</Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditKB(null); form.resetFields(); setEditOpen(true); }}>
            创建知识库
          </Button>
        </div>
      </div>

      {/* 知识库卡片网格 - 3列布局 */}
      <div className={styles.cardGrid}>
        {kbs.map((kb) => (
          <Card
            key={kb.id}
            hoverable
            loading={loading}
            bodyStyle={{ padding: '20px' }}
          >
            <div style={{ display: 'flex', gap: 16 }}>
              {/* 左侧彩色图标 */}
              <div style={{
                width: 48, height: 48, borderRadius: 10,
                backgroundColor: kb.is_public ? '#f0f5ff' : '#e6f4ff',
                color: kb.is_public ? '#597ef7' : '#1677ff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 24, flexShrink: 0,
              }}>
                {ICON_MAP[kb.icon || ''] || <DatabaseOutlined />}
              </div>

              {/* 右侧信息 */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <Text strong style={{ fontSize: 15 }}>{kb.name}</Text>
                  <StatusTag status={kb.is_public ? 'published' : 'draft'}
                    label={kb.is_public ? '公开' : '私有'} />
                </div>
                <Text type="secondary" style={{ fontSize: 13, display: 'block', marginBottom: 12 }}
                  ellipsis={{ rows: 2 }}>
                  {kb.description || '暂无描述'}
                </Text>

                {/* 底部统计与操作 */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Tooltip title="文档数量">
                    <span>
                      <FileTextOutlined style={{ color: '#8c8c8c', marginRight: 4 }} />
                      <Text strong>{kb.document_count}</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}> 文档</Text>
                    </span>
                  </Tooltip>
                  <Space size="small" onClick={(e) => e.stopPropagation()}>
                    <Button type="link" size="small" icon={<EditOutlined />}
                      onClick={() => { setEditKB(kb); form.setFieldsValue(kb); setEditOpen(true); }}>
                      编辑
                    </Button>
                    <Button type="link" size="small" danger icon={<DeleteOutlined />}
                      onClick={() => showConfirm()}>
                      删除
                    </Button>
                  </Space>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* 创建/编辑弹窗 */}
      <Modal title={editKB ? '编辑知识库' : '创建知识库'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={() => form.submit()} width={520} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={(_values) => {
          message.success(editKB ? '知识库更新成功' : '知识库创建成功');
          setEditOpen(false); loadData();
        }}>
          <Form.Item name="name" label="知识库名称" rules={[{ required: true, message: '请输入知识库名称' }]}>
            <Input placeholder="请输入知识库名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="请输入知识库描述" rows={3} />
          </Form.Item>
          <Form.Item name="is_public" label="是否公开" valuePropName="checked">
            <Switch checkedChildren="公开" unCheckedChildren="私有" />
          </Form.Item>
        </Form>
      </Modal>

      <ConfirmAction open={confirmOpen} title="删除知识库" content="确定要删除此知识库吗？" danger
        impactDescription="删除知识库将同时删除其中所有文档、Chunk、索引数据，且不可恢复"
        onOk={async () => { message.success('知识库已删除'); hideConfirm(); loadData(); }}
        onCancel={hideConfirm} confirmLoading={confirmLoading} />
    </div>
  );
}