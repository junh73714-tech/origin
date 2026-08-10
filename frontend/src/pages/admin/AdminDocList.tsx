/**
 * 管理后台 - 文档管理页面
 * 成员3：管理后台前端 - 4.4 知识库和文档
 * 文档上传、列表、状态管理、删除
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Modal, Upload, message } from 'antd';
import {
  UploadOutlined, DeleteOutlined, EyeOutlined, InboxOutlined,
  FilePdfOutlined, FileWordOutlined, FileExcelOutlined,
} from '@ant-design/icons';
import { DataTable, FilterBar, StatusTag, DetailDrawer, ConfirmAction } from '@/components/admin';
import { usePagination, useConfirmAction, useDetailDrawer } from '@/hooks/admin';
import type { Document } from '@/api/document';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload/interface';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;
const { Dragger } = Upload;

/** 文件类型图标 */
const FILE_TYPE_ICONS: Record<string, React.ReactNode> = {
  pdf: <FilePdfOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />,
  docx: <FileWordOutlined style={{ color: '#1677ff', fontSize: 20 }} />,
  doc: <FileWordOutlined style={{ color: '#1677ff', fontSize: 20 }} />,
  xlsx: <FileExcelOutlined style={{ color: '#52c41a', fontSize: 20 }} />,
  xls: <FileExcelOutlined style={{ color: '#52c41a', fontSize: 20 }} />,
};

/** 格式化文件大小 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * 文档管理页面
 */
export function AdminDocList() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: confirmOpen, confirmLoading, show: showConfirm, hide: hideConfirm } = useConfirmAction();
  const { open: drawerOpen, data: selectedDoc, show: showDetail, hide: hideDetail } = useDetailDrawer<Document>();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);

  // 模拟数据
  const mockDocs: Document[] = [
    { id: 'doc_001', knowledge_base_id: 'kb_001', name: '系统架构设计文档.pdf', file_type: 'pdf', file_size: 2540000, status: 'completed', char_count: 45000, current_version: 3, created_at: '2026-07-01', updated_at: '2026-07-15' },
    { id: 'doc_002', knowledge_base_id: 'kb_001', name: 'API接口规范.docx', file_type: 'docx', file_size: 1280000, status: 'completed', char_count: 32000, current_version: 2, created_at: '2026-07-02', updated_at: '2026-07-14' },
    { id: 'doc_003', knowledge_base_id: 'kb_002', name: '产品需求文档.pdf', file_type: 'pdf', file_size: 3800000, status: 'indexing', char_count: 68000, current_version: 1, created_at: '2026-07-10', updated_at: '2026-07-15' },
    { id: 'doc_004', knowledge_base_id: 'kb_002', name: '用户手册.docx', file_type: 'docx', file_size: 960000, status: 'parsing', char_count: 0, current_version: 1, created_at: '2026-07-14', updated_at: '2026-07-15' },
    { id: 'doc_005', knowledge_base_id: 'kb_003', name: '部署运维手册.pdf', file_type: 'pdf', file_size: 1800000, status: 'failed', char_count: 0, current_version: 1, created_at: '2026-07-12', updated_at: '2026-07-13' },
    { id: 'doc_006', knowledge_base_id: 'kb_003', name: '监控配置指南.xlsx', file_type: 'xlsx', file_size: 520000, status: 'completed', char_count: 12000, current_version: 1, created_at: '2026-07-05', updated_at: '2026-07-10' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setDocs(mockDocs); setLoading(false); }, 300);
  }, []);

  // 表格列
  const columns: ColumnsType<Document> = [
    { title: '文档名称', dataIndex: 'name', key: 'name', width: 250,
      render: (text: string, record: Document) => (
        <Space>{FILE_TYPE_ICONS[record.file_type] || <FilePdfOutlined />}
          <a onClick={() => showDetail(record)}>{text}</a></Space>
      ),
    },
    { title: '类型', dataIndex: 'file_type', key: 'file_type', width: 80, render: (t: string) => t.toUpperCase() },
    { title: '大小', dataIndex: 'file_size', key: 'file_size', width: 100,
      render: (size: number) => formatFileSize(size) },
    { title: '状态', dataIndex: 'status', key: 'status', width: 120,
      render: (status: string) => <StatusTag status={status} /> },
    { title: '版本', dataIndex: 'current_version', key: 'current_version', width: 60, align: 'center',
      render: (v: number) => <Text strong>v{v}</Text> },
    { title: '字符数', dataIndex: 'char_count', key: 'char_count', width: 100,
      render: (count: number) => count > 0 ? count.toLocaleString() : '-' },
    { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 140 },
    { title: '操作', key: 'action', width: 150, fixed: 'right',
      render: (_: unknown, record: Document) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => showDetail(record)}>详情</Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => showConfirm()}>删除</Button>
        </Space>
      ),
    },
  ];

  const filterItems = [
    { key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '文档名称' },
    { key: 'status', label: '状态', type: 'select' as const,
      options: [{ label: '已完成', value: 'completed' }, { label: '处理中', value: 'indexing' },
        { label: '解析中', value: 'parsing' }, { label: '失败', value: 'failed' }] },
  ];

  const detailItems = selectedDoc ? [
    { key: 'name', label: '文档名称', children: selectedDoc.name },
    { key: 'file_type', label: '文件类型', children: selectedDoc.file_type.toUpperCase() },
    { key: 'file_size', label: '文件大小', children: formatFileSize(selectedDoc.file_size) },
    { key: 'status', label: '状态', children: <StatusTag status={selectedDoc.status} /> },
    { key: 'current_version', label: '当前版本', children: `v${selectedDoc.current_version}` },
    { key: 'char_count', label: '字符数', children: selectedDoc.char_count?.toLocaleString() || '-' },
    { key: 'created_at', label: '创建时间', children: selectedDoc.created_at },
    { key: 'updated_at', label: '更新时间', children: selectedDoc.updated_at },
  ] : [];

  return (
    <div>
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={3} className={styles.pageTitle}>文档管理</Title>
            <Text type="secondary">管理知识库中的文档，支持上传、查看状态、删除操作</Text>
          </div>
          <Button type="primary" icon={<UploadOutlined />}
            onClick={() => { setFileList([]); setUploadOpen(true); }}>
            上传文档
          </Button>
        </div>
      </div>

      <FilterBar filters={filterItems} values={filters} onChange={handleFilterChange}
        onSearch={handleSearch} onReset={handleReset} />

      <DataTable<Document>
        columns={columns} dataSource={docs} rowKey="id"
        page={pagination.page} pageSize={pagination.page_size} total={docs.length}
        loading={loading} onChange={(page, pageSize) => handlePageChange(page, pageSize)}
        emptyDescription="暂无文档" emptyActionText="上传文档"
        onEmptyAction={() => { setFileList([]); setUploadOpen(true); }}
      />

      {/* 上传弹窗 */}
      <Modal title="上传文档" open={uploadOpen} onCancel={() => setUploadOpen(false)}
        footer={[
          <Button key="cancel" onClick={() => setUploadOpen(false)}>取消</Button>,
          <Button key="upload" type="primary" loading={uploading} disabled={fileList.length === 0}
            onClick={() => {
              setUploading(true);
              setTimeout(() => {
                message.success('文档上传成功，正在处理中');
                setUploading(false); setUploadOpen(false); loadData();
              }, 2000);
            }}>开始上传</Button>,
        ]} width={560} destroyOnClose>
        <Dragger multiple fileList={fileList} onChange={({ fileList }) => setFileList(fileList)}
          beforeUpload={() => false}
          accept=".pdf,.docx,.doc,.xlsx,.xls,.pptx,.ppt,.txt,.md,.html,.htm">
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">支持 PDF、DOCX、XLSX、PPTX、TXT、MD、HTML 格式，单文件最大 100MB</p>
        </Dragger>
      </Modal>

      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="文档详情" items={detailItems}
        footerActions={<Space><Button onClick={hideDetail}>关闭</Button></Space>} />

      <ConfirmAction open={confirmOpen} title="删除文档" content="确定要删除此文档吗？" danger
        impactDescription="删除文档将同时删除所有版本、Chunk 和索引数据，可能影响关联的标准问答"
        onOk={async () => { message.success('文档已删除'); hideConfirm(); loadData(); }}
        onCancel={hideConfirm} confirmLoading={confirmLoading} />
    </div>
  );
}