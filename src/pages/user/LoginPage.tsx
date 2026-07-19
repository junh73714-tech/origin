import { useEffect } from 'react';
import { Card, Typography } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { usePermissionStore } from '@/stores/permissionStore';
import { LoginForm } from '@/components/user/auth/LoginForm';
import type { LoginRequest } from '@/types/auth';

interface LocationState {
  from?: string;
}

/** 登录页 */
export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const authenticated = useAuthStore((s) => s.authenticated);
  const loading = useAuthStore((s) => s.loading);
  const error = useAuthStore((s) => s.error);
  const login = useAuthStore((s) => s.login);
  const loadPermissions = usePermissionStore((s) => s.load);

  const from = (location.state as LocationState | null)?.from || '/chat';

  useEffect(() => {
    if (authenticated) navigate(from, { replace: true });
  }, [authenticated, from, navigate]);

  const handleSubmit = async (values: LoginRequest) => {
    const ok = await login(values);
    if (ok) {
      await loadPermissions();
      navigate(from, { replace: true });
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f0f2f5',
      }}
    >
      <Card style={{ width: 380 }}>
        <Typography.Title level={3} style={{ textAlign: 'center', marginBottom: 4 }}>
          企业知识问答平台
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          请使用企业账号登录
        </Typography.Paragraph>
        <LoginForm loading={loading} error={error} onSubmit={handleSubmit} />
        <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginTop: 8 }}>
          演示账号（已在真后端预创建）：user / 123456（普通用户）、guest / 123456（无知识库权限）。
          注：禁用账号与连续输错锁定的演示由本地 Mock 模式（VITE_USE_MOCK=true）支持；当前真实后端暂未实现锁定接口。
        </Typography.Paragraph>
      </Card>
    </div>
  );
}
