/**
 * 管理后台 - 用户管理页面
 * 成员3：管理后台前端 - 4.2 用户与组织
 * 用户列表、创建、编辑、启用/禁用、搜索筛选分页
 */
import { useState, useCallback } from 'react';
import { Typography, Button, Space, Tag, Modal, Form, Input, Select, message } from 'antd';
import {
  PlusOutlined, EditOutlined, UserOutlined, MailOutlined, PhoneOutlined, LockOutlined,
} from '@ant-design/icons';
import { DataTable, FilterBar, StatusTag, DetailDrawer, ConfirmAction } from '@/components/admin';
import { useAdminStore } from '@/stores/admin';
import { usePagination, useConfirmAction, useDetailDrawer } from '@/hooks/admin';
import type { AdminUser } from '@/types/admin';
import type { ColumnsType } from 'antd/es/table';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

/**
 * 用户管理页面
 */
export function UserManagement() {
  const { pagination, filters, handlePageChange, handleFilterChange, handleSearch, handleReset } = usePagination();
  const { open: confirmOpen, confirmLoading, show: showConfirm, hide: hideConfirm } = useConfirmAction();
  const { open: drawerOpen, data: selectedUser, show: showDetail, hide: hideDetail } = useDetailDrawer<AdminUser>();
  const [editOpen, setEditOpen] = useState(false);
  const [editUser, setEditUser] = useState<AdminUser | null>(null);
  const [form] = Form.useForm();
  const { users, usersTotal, usersLoading, setUsers, setUsersLoading } = useAdminStore();

  // 模拟数据
  const mockUsers: AdminUser[] = [
    { id: 'usr_001', username: 'admin', email: 'admin@example.com', full_name: '系统管理员', phone: '13800000001', department_id: 'dept_001', department_name: '技术部', is_active: true, is_superuser: true, status: 'active', last_login_at: '2026-07-16 09:30:00', created_at: '2026-01-01', updated_at: '2026-07-15' },
    { id: 'usr_002', username: 'zhangsan', email: 'zhangsan@example.com', full_name: '张三', phone: '13800000002', department_id: 'dept_002', department_name: '产品部', is_active: true, is_superuser: false, status: 'active', last_login_at: '2026-07-16 08:15:00', created_at: '2026-02-15', updated_at: '2026-07-14' },
    { id: 'usr_003', username: 'lisi', email: 'lisi@example.com', full_name: '李四', phone: '13800000003', department_id: 'dept_001', department_name: '技术部', is_active: false, is_superuser: false, status: 'disabled', last_login_at: '2026-06-01', created_at: '2026-03-01', updated_at: '2026-06-15' },
    { id: 'usr_004', username: 'wangwu', email: 'wangwu@example.com', full_name: '王五', phone: '13800000004', department_id: 'dept_003', department_name: '运营部', is_active: true, is_superuser: false, status: 'active', last_login_at: '2026-07-15 18:00:00', created_at: '2026-04-01', updated_at: '2026-07-13' },
    { id: 'usr_005', username: 'zhaoliu', email: 'zhaoliu@example.com', full_name: '赵六', phone: '13800000005', department_id: 'dept_002', department_name: '产品部', is_active: true, is_superuser: false, status: 'locked', last_login_at: '2026-07-10', created_at: '2026-05-01', updated_at: '2026-07-12' },
  ];

  // 加载数据
  const loadData = useCallback(() => {
    setUsersLoading(true);
    // TODO: 替换为真实 API
    setTimeout(() => {
      setUsers(mockUsers, mockUsers.length);
      setUsersLoading(false);
    }, 300);
  }, [mockUsers, setUsers, setUsersLoading]);

  // 表格列
  const columns: ColumnsType<AdminUser> = [
    { title: '用户名', dataIndex: 'username', key: 'username', width: 120,
      render: (text: string, record: AdminUser) => <a onClick={() => showDetail(record)}>{text}</a> },
    { title: '姓名', dataIndex: 'full_name', key: 'full_name', width: 100 },
    { title: '邮箱', dataIndex: 'email', key: 'email', width: 200 },
    { title: '手机号', dataIndex: 'phone', key: 'phone', width: 140 },
    { title: '部门', dataIndex: 'department_name', key: 'department_name', width: 120,
      render: (text: string) => text || <Text type="secondary">未分配</Text> },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (status: string) => <StatusTag status={status} /> },
    { title: '角色', dataIndex: 'is_superuser', key: 'is_superuser', width: 100,
      render: (isSuper: boolean) => isSuper ? <Tag color="red">超级管理员</Tag> : <Tag>普通用户</Tag> },
    { title: '最后登录', dataIndex: 'last_login_at', key: 'last_login_at', width: 160,
      render: (text: string) => text || <Text type="secondary">从未登录</Text> },
    { title: '操作', key: 'action', width: 180, fixed: 'right',
      render: (_: unknown, record: AdminUser) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />}
            onClick={() => { setEditUser(record); form.setFieldsValue(record); setEditOpen(true); }}>
            编辑
          </Button>
          <Button type="link" size="small" danger={record.is_active}
            onClick={() => showConfirm()}>
            {record.is_active ? '禁用' : '启用'}
          </Button>
        </Space>
      ),
    },
  ];

  // 筛选配置
  const filterItems = [
    { key: 'keyword', label: '搜索', type: 'keyword' as const, placeholder: '用户名/姓名/邮箱' },
    { key: 'status', label: '状态', type: 'select' as const,
      options: [{ label: '已激活', value: 'active' }, { label: '已禁用', value: 'disabled' }, { label: '已锁定', value: 'locked' }] },
  ];

  // 详情配置
  const detailItems = selectedUser ? [
    { key: 'username', label: '用户名', children: selectedUser.username },
    { key: 'full_name', label: '姓名', children: selectedUser.full_name },
    { key: 'email', label: '邮箱', children: selectedUser.email },
    { key: 'phone', label: '手机号', children: selectedUser.phone || '-' },
    { key: 'department_name', label: '部门', children: selectedUser.department_name || '-' },
    { key: 'status', label: '状态', children: <StatusTag status={selectedUser.status} /> },
    { key: 'is_superuser', label: '角色', children: selectedUser.is_superuser ? '超级管理员' : '普通用户' },
    { key: 'last_login_at', label: '最后登录', children: selectedUser.last_login_at || '从未登录' },
    { key: 'created_at', label: '创建时间', children: selectedUser.created_at },
    { key: 'updated_at', label: '更新时间', children: selectedUser.updated_at },
  ] : [];

  return (
    <div>
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={3} className={styles.pageTitle}>用户管理</Title>
            <Text type="secondary">管理系统用户，包括创建、编辑、启用/禁用操作</Text>
          </div>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditUser(null); form.resetFields(); setEditOpen(true); }}>
            创建用户
          </Button>
        </div>
      </div>

      <FilterBar filters={filterItems} values={filters} onChange={handleFilterChange}
        onSearch={handleSearch} onReset={handleReset} />

      <DataTable<AdminUser>
        columns={columns} dataSource={users} rowKey="id"
        page={pagination.page} pageSize={pagination.page_size} total={usersTotal}
        loading={usersLoading} onChange={(page, pageSize) => handlePageChange(page, pageSize)}
        emptyDescription="暂无用户数据" emptyActionText="创建用户"
        onEmptyAction={() => { setEditUser(null); form.resetFields(); setEditOpen(true); }}
      />

      {/* 创建/编辑弹窗 */}
      <Modal title={editUser ? '编辑用户' : '创建用户'} open={editOpen}
        onCancel={() => setEditOpen(false)} onOk={() => form.submit()} width={520} destroyOnClose>
        <Form form={form} layout="vertical" onFinish={(values) => {
          message.success(editUser ? '用户更新成功' : '用户创建成功');
          setEditOpen(false); loadData();
        }}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="请输入用户名" />
          </Form.Item>
          <Form.Item name="full_name" label="姓名" rules={[{ required: true, message: '请输入姓名' }]}>
            <Input placeholder="请输入姓名" />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email', message: '请输入有效邮箱' }]}>
            <Input prefix={<MailOutlined />} placeholder="请输入邮箱" />
          </Form.Item>
          {!editUser && (
            <Form.Item name="password" label="密码" rules={[{ required: true, min: 6, message: '密码至少6位' }]}>
              <Input.Password prefix={<LockOutlined />} placeholder="请输入密码" />
            </Form.Item>
          )}
          <Form.Item name="phone" label="手机号">
            <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" />
          </Form.Item>
          <Form.Item name="department_id" label="部门">
            <Select placeholder="请选择部门" allowClear
              options={[{ label: '技术部', value: 'dept_001' }, { label: '产品部', value: 'dept_002' }, { label: '运营部', value: 'dept_003' }]} />
          </Form.Item>
        </Form>
      </Modal>

      <DetailDrawer open={drawerOpen} onClose={hideDetail} title="用户详情" items={detailItems}
        footerActions={<Space><Button onClick={hideDetail}>关闭</Button>
          <Button type="primary" icon={<EditOutlined />} onClick={() => {
            if (selectedUser) { form.setFieldsValue(selectedUser); setEditUser(selectedUser); setEditOpen(true); hideDetail(); }
          }}>编辑</Button></Space>} />

      <ConfirmAction open={confirmOpen} title="确认操作" content="确定要对此用户执行此操作吗？" danger
        impactDescription="禁用后该用户将无法登录系统，正在进行的会话将被终止"
        onOk={async () => { message.success('操作成功'); hideConfirm(); }}
        onCancel={hideConfirm} confirmLoading={confirmLoading} />
    </div>
  );
}