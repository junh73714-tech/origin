import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { LoginForm } from '@/components/user/auth/LoginForm';

describe('LoginForm 登录表单', () => {
  it('必填项校验：空提交不触发 onSubmit', async () => {
    const onSubmit = vi.fn();
    render(<LoginForm loading={false} error={null} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole('button', { name: /登.*录/ }));
    await waitFor(() => {
      expect(screen.getByText('请输入用户名')).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('填写后提交触发 onSubmit', async () => {
    const onSubmit = vi.fn();
    render(<LoginForm loading={false} error={null} onSubmit={onSubmit} />);
    fireEvent.change(screen.getByPlaceholderText('请输入用户名'), {
      target: { value: 'user' },
    });
    fireEvent.change(screen.getByPlaceholderText('请输入密码'), {
      target: { value: '123456' },
    });
    fireEvent.click(screen.getByRole('button', { name: /登.*录/ }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith({ username: 'user', password: '123456' });
    });
  });

  it('展示错误提示且不暴露堆栈', () => {
    render(
      <LoginForm loading={false} error="用户名或密码错误。" onSubmit={vi.fn()} />,
    );
    expect(screen.getByRole('alert')).toHaveTextContent('用户名或密码错误。');
  });
});
