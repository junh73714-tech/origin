/**
 * 管理后台 - 部门管理页面
 * 成员3：管理后台前端 - 4.2 用户与组织
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Modal, Form, Input, TreeSelect, message, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, TeamOutlined } from '@ant-design/icons';
import { DataTable, FilterBar, ConfirmAction } from '@/components/admin';
import { usePagination, useConfirmAction } from '@/hooks/admin';
import type { Department } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

export function DepartmentManagement() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: confirmOpen, confirmLoading, show: showConfirm, hide: hideConfirm } = useConfirmAction();
  const [editOpen, setEditOpen] = useState(false);
  const [editDept, setEditDept] = useState<Department | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const mockDepts: Department[] = [
    { id: 'dept_001', name: '技术部', parent_id: undefined, manager_id: 'usr_001', manager_name: '系统管理员', member_count: 25, description: '负责技术研发和架构设计', created_at: '2026-01-01', updated_at: '2026-07-01' },
    { id: 'dept_002', name: '产品部', parent_id: undefined, manager_id: 'usr_002', manager_name: '张三', member_count: 15, description: '产品规划和需求管理', created_at: '2026-01-15', updated_at: '2026-06-15' },
    { id: 'dept_003', name: '运营部', parent_id: undefined, manager_id: 'usr_004', manager_name: '王五', member_count: 12, description: '日常运营和客户服务', created_at: '2026-02-01', updated_at: '2026-07-01' },
    { id: 'dept_004', name: '前端组', parent_id: 'dept_001', parent_name: '技术部', manager_id: undefined, member_count: 8, description: 'Web前端开发', created_at: '2026-03-01', updated_at: '2026-06-01' },
    { id: 'dept_005', name: '后端组', parent_id: 'dept_001', parent_name: '技术部', manager_id: undefined, member_count: 10, description: '后端服务和API开发', created_at: '2026-03-01', updated_at: '2026-06-01' },
  ];

  const loadData = useCallback(() => {
    setLoading(true);
    setTimeout(() => { setDepartments(mockDepts); setLoading(false); }, 300);
  }, []);

  const columns: ColumnsType<Department> = [
    { title: '部门名称', dataIndex: 'name', key: 'name', width: 150 },
    { title: '上级部门', dataIndex: 'parent_name', key: 'parent_name', width: 120,
      render: (text: string) => text || <Tag color="red">顶级部门</Tag> },
    { title: '负责人', dataIndex: 'manager_name', key: 'manager_name', width: 120,
      render: (text: string) => text || <Text type="secondary">未指定</Text> },
    { title: '成员数', dataIndex: 'member_count', key: 'member_count', width: 80, align: 'center',
      render: (count: number) => <Space><TeamOutlined /><Text strong>{count}</Text></Space> },
    { title: '描述', dataIndex: 'description', key: 'description', width: 200, ellipsis: true },
    { title: '操作', key: 'action', width: 150, fixed: 'right',
      render: (_: unknown, record: Department) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />}
            onClick={() => { setEditDept(record); form.setFieldsValue(record); setEditOpen(true); }}>编辑</Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => showConfirm()}>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={3} className={styles.pageTitle}>部门管理</Title>
            <Text type="secondary">管理组织部门结构，支持树形层级</Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditDept(null); form.resetFields(); setEditOpen(true); }}>创建部门</Button>
        </div>
      </div>
      <FilterBar
        filters={[{ key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '部门名称' }]}
        values={filters} onChange={handleFilterChange} onSearch={handleSearch} onReset={handleReset} />
      <DataTable<Department> columns={columns} dataSource={departments} rowKey="id"
        page={pagination.page} pageSize={pagination.page_size} total={departments.length}
        loading={loading} onChange={(page, pageSize) => handlePageChange(page, pageSize)}
        emptyDescription="暂无部门数据" emptyActionText="创建部门"
        onEmptyAction={() => { setEditDept(null); form.resetFields(); setEditOpen(true); }} />
      <Modal title={editDept ? '编辑部门' : '创建部门'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={() => form.submit()} width={480} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={(_values) => {
          message.success(editDept ? '部门更新成功' : '部门创建成功');
          setEditOpen(false); loadData();
        }}>
          <Form.Item name="name" label="部门名称" rules={[{ required: true }]}>
            <Input placeholder="请输入部门名称" />
          </Form.Item>
          <Form.Item name="parent_id" label="上级部门">
            <TreeSelect treeData={departments.map(d => ({ title: d.name, value: d.id, key: d.id }))}
              placeholder="请选择上级部门（可选）" allowClear />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="请输入部门描述" rows={2} />
          </Form.Item>
        </Form>
      </Modal>
      <ConfirmAction open={confirmOpen} title="删除部门" content="确定要删除此部门吗？" danger
        impactDescription="删除部门将影响部门内所有用户，子部门将移至根级"
        onOk={async () => { message.success('部门已删除'); hideConfirm(); loadData(); }}
        onCancel={hideConfirm} confirmLoading={confirmLoading} />
    </div>
  );
}