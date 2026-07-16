import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { Layout } from '@/layouts/shared';
import { useAuthStore } from '@/store/auth';

// 页面组件 - 后续由成员2、3实现
const LoginPage = () => <div>登录页面</div>;
const HomePage = () => <div>首页</div>;
const ChatPage = () => <div>问答页面</div>;
const HistoryPage = () => <div>历史记录</div>;
const KnowledgeBaseListPage = () => <div>知识库列表</div>;
const DocumentListPage = () => <div>文档列表</div>;
const QAListPage = () => <div>问答列表</div>;
const AdminDashboard = () => <div>管理后台</div>;
const UserManagePage = () => <div>用户管理</div>;
const RoleManagePage = () => <div>角色管理</div>;

function App() {
  const { checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  return (
    <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<LoginPage />} />

      {/* 受保护的路由 */}
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/home" replace />} />
        <Route path="/home" element={<HomePage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:conversationId" element={<ChatPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/knowledge-bases" element={<KnowledgeBaseListPage />} />
        <Route path="/knowledge-bases/:kbId/documents" element={<DocumentListPage />} />
        <Route path="/qa" element={<QAListPage />} />
      </Route>

      {/* 管理后台路由 */}
      <Route element={<Layout />}>
        <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="/admin/dashboard" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<UserManagePage />} />
        <Route path="/admin/roles" element={<RoleManagePage />} />
      </Route>

      {/* 404 */}
      <Route path="*" element={<div>404 Not Found</div>} />
    </Routes>
  );
}

export default App;
