/**
 * 管理后台布局组件
 * 成员3：管理后台前端
 * 三栏结构：左侧侧边栏（目录树）+ 顶部导航栏 + 右侧主内容区
 * 顶部导航：品牌 Logo + Tab 导航 + 用户操作
 * 侧边栏：树形目录菜单，按权限过滤
 */
import { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, Input, Badge, Tooltip } from 'antd';
import type { MenuProps } from 'antd';
import {
  // 侧边栏图标
  DashboardOutlined,
  UserOutlined,
  SafetyOutlined,
  DatabaseOutlined,
  QuestionCircleOutlined,
  SearchOutlined,
  ExperimentOutlined,
  AuditOutlined,
  SettingOutlined,
  // 顶部图标
  BellOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined as SidebarSearchIcon,
  GlobalOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuthStore } from '@/store/auth';
import styles from './AdminLayout.module.css';

const { Header, Sider, Content } = Layout;

/**
 * 管理后台菜单配置
 * 每个菜单项可配置 permission_code 用于权限过滤
 */
const ADMIN_MENU_ITEMS: MenuProps['items'] = [
  // 工作台
  {
    key: '/admin/dashboard',
    icon: <DashboardOutlined />,
    label: '工作台',
  },
  // 用户与组织
  {
    key: 'user-group',
    icon: <UserOutlined />,
    label: '用户与组织',
    children: [
      { key: '/admin/users', label: '用户管理' },
      { key: '/admin/departments', label: '部门管理' },
      { key: '/admin/user-groups', label: '用户组管理' },
      { key: '/admin/roles', label: '角色管理' },
      { key: '/admin/temp-auth', label: '临时授权' },
    ],
  },
  // 权限中心
  {
    key: 'permission-group',
    icon: <SafetyOutlined />,
    label: '权限中心',
    children: [
      { key: '/admin/permissions', label: '功能权限' },
      { key: '/admin/data-permissions', label: '数据权限' },
      { key: '/admin/kb-auth', label: '知识库授权' },
      { key: '/admin/doc-classification', label: '文档密级' },
      { key: '/admin/permission-rules', label: '权限规则' },
      { key: '/admin/permission-audit', label: '权限审计' },
    ],
  },
  // 知识库与文档
  {
    key: 'kb-group',
    icon: <DatabaseOutlined />,
    label: '知识库与文档',
    children: [
      { key: '/admin/knowledge-bases', label: '知识库列表' },
      { key: '/admin/documents', label: '文档管理' },
      { key: '/admin/document-versions', label: '文档版本' },
      { key: '/admin/chunks', label: 'Chunk 查看' },
      { key: '/admin/index-tasks', label: '索引任务' },
    ],
  },
  // 问答优化
  {
    key: 'qa-group',
    icon: <QuestionCircleOutlined />,
    label: '问答优化',
    children: [
      { key: '/admin/candidate-qa', label: '候选问答' },
      { key: '/admin/pending-review', label: '待审核问答' },
      { key: '/admin/standard-qa', label: '标准问答' },
      { key: '/admin/similar-questions', label: '相似问句' },
      { key: '/admin/frequent-questions', label: '高频问题' },
      { key: '/admin/unmatched-questions', label: '未命中问题' },
      { key: '/admin/low-quality-answers', label: '低质量答案' },
    ],
  },
  // 检索调试
  {
    key: '/admin/search-debug',
    icon: <SearchOutlined />,
    label: '检索调试',
  },
  // 评估中心
  {
    key: 'eval-group',
    icon: <ExperimentOutlined />,
    label: '评估中心',
    children: [
      { key: '/admin/evaluation/datasets', label: 'Golden Dataset' },
      { key: '/admin/evaluation/samples', label: '评估样本' },
      { key: '/admin/evaluation/tasks', label: '评估任务' },
      { key: '/admin/evaluation/history', label: '历史评估' },
      { key: '/admin/evaluation/compare', label: '参数对比' },
    ],
  },
  // 安全与审计
  {
    key: 'audit-group',
    icon: <AuditOutlined />,
    label: '安全与审计',
    children: [
      { key: '/admin/logs/query', label: '查询日志' },
      { key: '/admin/logs/operation', label: '操作日志' },
      { key: '/admin/logs/login', label: '登录日志' },
      { key: '/admin/security/events', label: '安全事件' },
      { key: '/admin/security/alerts', label: '风险告警' },
    ],
  },
  // 系统设置
  {
    key: 'settings-group',
    icon: <SettingOutlined />,
    label: '系统设置',
    children: [
      { key: '/admin/settings/llm', label: 'LLM 配置' },
      { key: '/admin/settings/embedding', label: 'Embedding 配置' },
      { key: '/admin/settings/reranker', label: 'Reranker 配置' },
      { key: '/admin/settings/ocr', label: 'OCR 配置' },
      { key: '/admin/settings/retrieval', label: '检索参数' },
      { key: '/admin/settings/prompts', label: '提示词模板' },
      { key: '/admin/settings/health', label: '系统健康' },
    ],
  },
];

/**
 * 管理后台布局组件
 */
export function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();

  // 获取当前选中的菜单 key
  const selectedKeys = [location.pathname];

  // 获取当前展开的菜单组
  const openKeys = (ADMIN_MENU_ITEMS || [])
    .filter((item) => item && 'children' in item && item.children)
    .map((item) => item!.key as string);

  /**
   * 用户下拉菜单
   */
  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '账号设置',
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  /**
   * 处理用户菜单点击
   */
  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      logout();
      navigate('/login');
    } else if (key === 'profile') {
      navigate('/admin/profile');
    }
  };

  /**
   * 处理侧边栏菜单点击
   */
  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (key && !key.includes('group')) {
      navigate(key);
    }
  };

  /**
   * 顶部 Tab 导航项
   */
  const topTabs = [
    { key: '/admin/dashboard', label: '工作台' },
    { key: '/admin/users', label: '用户管理' },
    { key: '/admin/knowledge-bases', label: '知识库' },
    { key: '/admin/standard-qa', label: '问答管理' },
  ];

  return (
    <Layout className={styles.adminLayout}>
      {/* ========== 左侧侧边栏 ========== */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={220}
        collapsedWidth={60}
        className={styles.adminSider}
      >
        {/* 侧边栏顶部搜索 */}
        {!collapsed && (
          <div className={styles.siderSearch}>
            <Input
              placeholder="搜索菜单..."
              prefix={<SidebarSearchIcon />}
              size="small"
              style={{
                borderRadius: 6,
                background: '#f5f6f8',
                border: 'none',
              }}
            />
          </div>
        )}

        {/* 菜单 */}
        <Menu
          mode="inline"
          selectedKeys={selectedKeys}
          defaultOpenKeys={collapsed ? [] : openKeys}
          items={ADMIN_MENU_ITEMS}
          onClick={handleMenuClick}
          className={styles.siderMenu}
          style={{ marginTop: collapsed ? 16 : 0 }}
        />

        {/* 折叠按钮 */}
        <div
          className={styles.siderCollapseBtn}
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </div>
      </Sider>

      {/* ========== 右侧主区域 ========== */}
      <Layout>
        {/* ========== 顶部导航栏 ========== */}
        <Header className={styles.adminHeader}>
          {/* 左侧：品牌 Logo + Tab 导航 */}
          <div className={styles.headerLeft}>
            <div className={styles.brandLogo}>
              <div className={styles.brandLogoIcon}>R</div>
              {!collapsed && <span>RAG 管理后台</span>}
            </div>

            {/* 顶部 Tab 导航 */}
            <div className={styles.headerTabs}>
              {topTabs.map((tab) => {
                const isActive = location.pathname.startsWith(tab.key);
                return (
                  <div
                    key={tab.key}
                    className={isActive ? styles.headerTabActive : styles.headerTab}
                    onClick={() => navigate(tab.key)}
                  >
                    {tab.label}
                  </div>
                );
              })}
            </div>
          </div>

          {/* 右侧：图标按钮 + 用户信息 */}
          <div className={styles.headerRight}>
            {/* 通知图标 */}
            <Tooltip title="通知">
              <div className={styles.headerIconBtn}>
                <Badge count={3} size="small">
                  <BellOutlined style={{ fontSize: 16 }} />
                </Badge>
              </div>
            </Tooltip>

            {/* 全局搜索 */}
            <Tooltip title="全局搜索">
              <div className={styles.headerIconBtn}>
                <GlobalOutlined style={{ fontSize: 16 }} />
              </div>
            </Tooltip>

            {/* 用户头像和下拉菜单 */}
            <Dropdown
              menu={{ items: userMenuItems, onClick: handleUserMenuClick }}
              placement="bottomRight"
            >
              <div className={styles.userInfo}>
                <Avatar
                  size="small"
                  icon={<UserOutlined />}
                  style={{ backgroundColor: '#1677ff' }}
                />
                <span className={styles.username}>
                  {user?.full_name || user?.username || '管理员'}
                </span>
              </div>
            </Dropdown>
          </div>
        </Header>

        {/* ========== 主内容区域 ========== */}
        <Content className={styles.adminContent}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}