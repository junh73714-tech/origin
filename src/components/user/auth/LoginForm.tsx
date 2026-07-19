import { Button, Form, Input, Alert } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useState } from 'react';
import type { LoginRequest } from '@/types/auth';

interface LoginFormProps {
  loading: boolean;
  error: string | null;
  onSubmit: (values: LoginRequest) => void;
}

/** 登录表单：校验、防重复提交、失败提示（不暴露堆栈） */
export function LoginForm({ loading, error, onSubmit }: LoginFormProps) {
  const [form] = Form.useForm<LoginRequest>();
  const [submitting, setSubmitting] = useState(false);

  const handleFinish = (values: LoginRequest) => {
    if (submitting || loading) return; // 防重复提交
    setSubmitting(true);
    onSubmit(values);
    // 结果由父组件通过 loading/error 反馈；此处仅短暂锁定
    setTimeout(() => setSubmitting(false), 600);
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
        <Button
          type="primary"
          htmlType="submit"
          block
          loading={loading || submitting}
        >
          登录
        </Button>
      </Form.Item>
    </Form>
  );
}
