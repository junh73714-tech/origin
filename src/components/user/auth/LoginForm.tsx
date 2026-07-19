import { Button, Form, Input, Alert, Space, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { LoginRequest } from '@/types/auth';

interface LoginFormProps {
  loading: boolean;
  error: string | null;
  onSubmit: (values: LoginRequest) => void;
}

/** 演示账号种子：用于真实后端联调时一键创建演示用户。
 *  对应后端真实用户：user (普通)、guest (无 KB 权限)。locked 由 Mock 模式承担。
 */
const DEMO_ACCOUNTS: Array<{
  username: string;
  email: string;
  password: string;
  full_name: string;
}> = [
  { username: 'user',  email: 'user@example.com',  password: '123456', full_name: '张晓明' },
  { username: 'guest', email: 'guest@example.com', password: '123456', full_name: '访客用户' },
];

/** 登录表单：校验、防重复提交、失败提示（不暴露堆栈）。
 *  在真实后端模式下，提供"创建演示账号"工具按钮，便于联调首次环境。 */
export function LoginForm({ loading, error, onSubmit }: LoginFormProps) {
  const [form] = Form.useForm<LoginRequest>();
  const [submitting, setSubmitting] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const isMock = import.meta.env.VITE_USE_MOCK === 'true';

  const handleFinish = (values: LoginRequest) => {
    if (submitting || loading) return; // 防重复提交
    setSubmitting(true);
    onSubmit(values);
    setTimeout(() => setSubmitting(false), 600);
  };

  /** 调用真实后端 /auth/register 创建演示账号；已存在会返回 400，忽略即可 */
  const handleSeed = async () => {
    setSeeding(true);
    let ok = 0;
    let existed = 0;
    let failed = 0;
    for (const u of DEMO_ACCOUNTS) {
      try {
        const resp = await fetch(
          `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/auth/register`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(u),
          },
        );
        if (resp.ok) {
          ok += 1;
        } else if (resp.status === 400 || resp.status === 409) {
          existed += 1;
        } else {
          failed += 1;
        }
      } catch {
        failed += 1;
      }
    }
    setSeeding(false);
    if (failed === 0) {
      const summary =
        ok > 0 && existed > 0
          ? `已创建 ${ok} 个，已存在 ${existed} 个`
          : ok > 0
          ? `已创建 ${ok} 个演示账号`
          : `演示账号已存在（${existed} 个）`;
      message.success(summary + '，可直接登录 user / 123456 或 guest / 123456');
    } else {
      message.error(`创建失败 ${failed} 个，请检查后端是否可访问`);
    }
  };

  return (
    <Form form={form} layout="vertical" onFinish={handleFinish} disabled={loading}>
      {error ? (
        <Form.Item>
          <Alert type="error" message={error} showIcon role="alert" />
        </Form.Item>
      ) : null}
      <Form.Item
        label="用户名"
        name="username"
        rules={[{ required: true, message: '请输入用户名' }]}
      >
        <Input prefix={<UserOutlined />} placeholder="请输入用户名" autoComplete="username" />
      </Form.Item>
      <Form.Item
        label="密码"
        name="password"
        rules={[{ required: true, message: '请输入密码' }]}
      >
        <Input.Password
          prefix={<LockOutlined />}
          placeholder="请输入密码"
          autoComplete="current-password"
        />
      </Form.Item>
      <Form.Item>
        <Space direction="vertical" style={{ width: '100%' }} size="small">
          <Button
            type="primary"
            htmlType="submit"
            block
            loading={loading || submitting}
          >
            登录
          </Button>
          {!isMock ? (
            <Button block size="small" type="link" loading={seeding} onClick={handleSeed}>
              一键创建演示账号（真后端环境用）
            </Button>
          ) : null}
        </Space>
      </Form.Item>
    </Form>
  );
}
