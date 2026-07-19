import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AuthGuard } from '@/components/user/auth/AuthGuard';
import { UserLayout } from '@/pages/user/UserLayout';
import { LoginPage } from '@/pages/user/LoginPage';
import { ChatPage } from '@/pages/user/ChatPage';
import { HistoryPage } from '@/pages/user/HistoryPage';
import { ProfilePage } from '@/pages/user/ProfilePage';

// 说明：正式集成时用户端路由由成员1的共享路由框架挂载；
// 本工程提供独立路由入口用于成员2模块自测。
export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <AuthGuard>
        <UserLayout />
      </AuthGuard>
    ),
    children: [
      { index: true, element: <Navigate to="/chat" replace /> },
      { path: 'chat', element: <ChatPage /> },
      { path: 'chat/:conversationId', element: <ChatPage /> },
      { path: 'history', element: <HistoryPage /> },
      { path: 'profile', element: <ProfilePage /> },
    ],
  },
  { path: '*', element: <Navigate to="/chat" replace /> },
]);
