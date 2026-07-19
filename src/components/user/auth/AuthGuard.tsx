import { Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuthStore } from '@/stores/authStore';

interface AuthGuardProps {
  children: ReactNode;
}

/** 路由守卫：仅用于用户体验，不替代后端鉴权。未认证跳登录页。 */
export function AuthGuard({ children }: AuthGuardProps) {
  const authenticated = useAuthStore((s) => s.authenticated);
  const location = useLocation();

  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}
