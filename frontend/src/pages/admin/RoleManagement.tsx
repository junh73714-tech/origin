/**
 * 管理后台 - 角色管理页面
 * 成员3：管理后台前端 - 4.2 用户与组织
 * 角色列表、创建、编辑、权限分配、删除
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Modal, Form, Input, Tree, message, Tag } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SafetyOutlined } from '@ant-design/icons';
import { DataTable, FilterBar, DetailDrawer, ConfirmAction } from '@/components/admin';
import { useAdminStore } from '@/stores/admin';
import { usePagination, useConfirmAction, useDetailDrawer } from '@/hooks/admin';
import type { Role } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

/** 模拟权限树 */
const MOCK_PERMISSIONS = [
  { key: 'user', title: '用户管理', children: [
    { key: 'user:view', title: '查看用户' }, { key: 'user:create', title: '创建用户' },
    { key: 'user:edit', title: '编辑用户' }, { key: 'user:delete', title: '删除用户' },
  ]},
  { key: 'role', title: '角色管理', children: [
    { key: 'role:view', title: '查看角色' }, { key: 'role:create', title: '创建角色' },
    { key: 'role:edit', title: '编辑角色' }, { key: 'role:delete', title: '删除角色' },
  ]},
  { key: 'kb', title: '知识库管理', children: [
    { key: 'kb:view', title: '查看知识库' }, { key: 'kb:create', title: '创建知识库' },
    { key: 'kb:edit', title: '编辑知识库' }, { key: 'kb:delete', title: '删除知识库' },
  ]},
  { key: 'doc', title: '文档管理', children: [
    { key: 'doc:upload', title: '上传文档' }, { key: 'doc:view', title: '查看文档' },
    { key: 'doc:delete', title: '删除文档' },
  ]},
  { key: 'qa', title: '问答管理', children: [
    { key: 'qa:review', title: '审核问答' }, { key: 'qa:publish', title: '发布问答' },
  ]},
];

/**
 * 角色管理页面
 */
export function RoleManagement() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: confirmOpen, confirmLoading, show: showConfirm, hide: hideConfirm } = useConfirmAction();
  const { open: drawerOpen, data: selectedRole, show: showDetail, hide: hideDetail } = useDetailDrawer<Role>();
  const [editOpen, setEditOpen] = useState(false);
  const [editRole, setEditRole] = useState<Role | null>(null);
  const [checkedKeys, setCheckedKeys] = useState<string[]>([]);
  const [form] = Form.useForm();
  const { roles, rolesLoading, setRoles, setRolesLoading } = useAdminStore();

  // 模拟数据
  const mockRoles: Role[] = [
    { id: 'role_001', name: '超级管理员', code: 'super_admin', description: '系统全部权限', is_system: true, user_count: 1, permission_count: 18, created_at: '2026-01-01', updated_at: '2026-01-01' },
    { id: 'role_002', name: '知识库管理员', code: 'kb_admin', description: '知识库和文档管理权限', is_system: false, user_count: 3, permission_count: 8, created_at: '2026-02-01', updated_at: '2026-06-15' },
    { id: 'role_003', name: '问答审核员', code: 'qa_reviewer', description: '问答审核和发布权限', is_system: false, user_count: 2, permission_count: 4, created_at: '2026-03-01', updated_at: '2026-07-01' },
    { id: 'role_004', name: '普通用户', code: 'user', description: '基本查看权限', is_system: true, user_count: 10, permission_count: 3, created_at: '2026-01-01', updated_at: '2026-01-01' },
  ];

  const loadData = useCallback(() => {
    setRolesLoading(true);
    setTimeout(() => { setRoles(mockRoles); setRolesLoading(false); }, 300);
  }, [mockRoles, setRoles, setRolesLoading]);

  const columns: ColumnsType<Role> = [
    { title: '角色名称', dataIndex: 'name', key: 'name', width: 150,
      render: (text: string, record: Role) => <a onClick={() => showDetail(record)}>{text}</a> },
    { title: '角色编码', dataIndex: 'code', key: 'code', width: 160, render: (text: string) => <Text code>{text}</Text> },
    { title: '描述', dataIndex: 'description', key: 'description', width: 200, ellipsis: true },
    { title: '类型', dataIndex: 'is_system', key: 'is_system', width: 100,
      render: (isSystem: boolean) => isSystem ? <Tag color="blue">系统内置</Tag> : <Tag>自定义</Tag> },
    { title: '用户数', dataIndex: 'user_count', key: 'user_count', width: 80, align: 'center' },
    { title: '权限数', dataIndex: 'permission_count', key: 'permission_count', width: 80, align: 'center' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 120 },
    { title: '操作', key: 'action', width: 200, fixed: 'right',
      render: (_: unknown, record: Role) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />}
            onClick={() => { setEditRole(record); form.setFieldsValue(record); setCheckedKeys([]); setEditOpen(true); }}>
            编辑
          </Button>
          <Button type="link" size="small" icon={<SafetyOutlined />}
            onClick={() => { setEditRole(record); setCheckedKeys([]); setEditOpen(true); }}>
            权限
          </Button>
          {!record.is_system && (
            <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => showConfirm()}>
              删除
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const filterItems = [
    { key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '角色名称/编码' },
  ];

  const detailItems = selectedRole ? [
    { key: 'name', label: '角色名称', children: selectedRole.name },
    { key: 'code', label: '角色编码', children: <Text code>{selectedRole.code}</Text> },
    { key: 'description', label: '描述', children: selectedRole.description || '-' },
    { key: 'is_system', label: '类型', children: selectedRole.is_system ? <Tag color="blue">系统内置</Tag> : <Tag>自定义</Tag> },
    { key: 'user_count', label: '关联用户数', children: selectedRole.user_count },
    { key: 'permission_count', label: '权限数量', children: selectedRole.permission_count },
    { key: 'created_at', label: '创建时间', children: selectedRole.created_at },
  ] : [];

  return (
    <div>
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={3} className={styles.pageTitle}>角色管理</Title>
            <Text type="secondary">管理角色定义和权限分配，系统内置角色不可删除</Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditRole(null); form.resetFields(); setCheckedKeys([]); setEditOpen(true); }}>
            创建角色
          </Button>
        </div>
      </div>

      <FilterBar filters={filterItems} values={filters} onChange={handleFilterChange}
        onSearch={handleSearch} onReset={handleReset} />

      <DataTable<Role>
        columns={columns} dataSource={roles} rowKey="id"
        page={pagination.page} pageSize={pagination.page_size} total={roles.length}
        loading={rolesLoading} onChange={(page, pageSize) => handlePageChange(page, pageSize)}
        emptyDescription="暂无角色数据" emptyActionText="创建角色"
        onEmptyAction={() => { setEditRole(null); form.resetFields(); setEditOpen(true); }}
      />

      {/* 创建/编辑弹窗 */}
      <Modal title={editRole ? '编辑角色' : '创建角色'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={() => form.submit()} width={640} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={(_values) => {
          message.success(editRole ? '角色更新成功' : '角色创建成功');
          setEditOpen(false); loadData();
        }}>
          <Form.Item name="name" label="角色名称" rules={[{ required: true, message: '请输入角色名称' }]}>
            <Input placeholder="请输入角色名称" />
          </Form.Item>
          <Form.Item name="code" label="角色编码" rules={[{ required: true, message: '请输入角色编码' }]}>
            <Input placeholder="请输入角色编码（如 kb_admin）" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="请输入角色描述" rows={2} />
          </Form.Item>
          <Form.Item label="权限分配">
            <Tree
              checkable defaultExpandAll
              treeData={MOCK_PERMISSIONS}
              checkedKeys={checkedKeys}
              onCheck={(keys) => setCheckedKeys(keys as string[])}
            />
          </Form.Item>
        </Form>
      </Modal>

      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="角色详情" items={detailItems}
        footerActions={<Space><Button onClick={hideDetail}>关闭</Button>
          <Button type="primary" icon={<EditOutlined />} onClick={() => {
            if (selectedRole) { form.setFieldsValue(selectedRole); setEditRole(selectedRole); setEditOpen(true); hideDetail(); }
          }}>编辑</Button></Space>} />

      <ConfirmAction open={confirmOpen} title="删除角色" content="确定要删除此角色吗？" danger
        impactDescription="删除角色后，已分配此角色的用户将失去对应权限，请确认影响范围"
        onOk={async () => { message.success('角色已删除'); hideConfirm(); loadData(); }}
        onCancel={hideConfirm} confirmLoading={confirmLoading} />
    </div>
  );
}