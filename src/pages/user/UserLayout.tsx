import { Layout, Menu, Avatar, Dropdown, Typography } from 'antd';
import {
  MessageOutlined,
  HistoryOutlined,
  UserOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { CitationDrawer } from '@/components/user/citation/CitationDrawer';

const { Header, Sider, Content } = Layout;

/** 用户端主布局：侧边导航 + 顶部用户信息 + 内容区。全局挂载引用抽屉。 */
export function UserLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const selectedKey = location.pathname.startsWith('/history')
    ? '/history'
    : location.pathname.startsWith('/profile')
      ? '/profile'
      : '/chat';

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light" width={200} breakpoint="lg" collapsedWidth={0}>
        <div style={{ padding: 16, fontWeight: 600, fontSize: 16 }}>知识问答</div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          onClick={({ key }) => navigate(key)}
          items={[
            { key: '/chat', icon: <MessageOutlined />, label: '智能问答' },
            { key: '/history', icon: <HistoryOutlined />, label: '历史会话' },
            { key: '/profile', icon: <UserOutlined />, label: '个人信息' },
          ]}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            display: 'flex',
            justifyContent: 'flex-end',
            alignItems: 'center',
            paddingInline: 24,
          }}
        >
          <Dropdown
            menu={{
              items: [
                { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
              ],
              onClick: ({ key }) => {
                if (key === 'logout') handleLogout();
              },
            }}
          >
            <span style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} style={{ marginRight: 8 }} />
              <Typography.Text>{user?.display_name || '用户'}</Typography.Text>
            </span>
          </Dropdown>
        </Header>
        <Content style={{ margin: 16 }}>
          <Outlet />
        </Content>
      </Layout>
      <CitationDrawer />
    </Layout>
  );
}
