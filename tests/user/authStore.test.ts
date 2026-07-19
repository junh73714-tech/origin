import { describe, it, expect, beforeEach } from 'vitest';
import { useAuthStore } from '@/stores/authStore';
import { usePermissionStore } from '@/stores/permissionStore';
import { useChatStore } from '@/stores/chat/chatStore';
import { tokenStore } from '@/stores/tokenStore';
import { authMock } from '@/mocks/authMock';
import { ErrorCode } from '@/types/common';

// 验证认证生命周期与切换用户后的缓存清理
describe('authStore 认证与缓存清理', () => {
  beforeEach(() => {
    useAuthStore.getState().forceLogout();
  });

  it('正确账号登录成功并加载用户', async () => {
    const ok = await useAuthStore.getState().login({ username: 'user', password: '123456' });
    expect(ok).toBe(true);
    expect(useAuthStore.getState().authenticated).toBe(true);
    expect(useAuthStore.getState().user?.username).toBe('user');
    expect(tokenStore.getAccess()).toBeTruthy();
  });

  it('禁用账号登录失败并给出提示', async () => {
    const ok = await useAuthStore.getState().login({ username: 'locked', password: '123456' });
    expect(ok).toBe(false);
    expect(useAuthStore.getState().authenticated).toBe(false);
    expect(useAuthStore.getState().error).toContain('禁用');
  });

  it('错误密码登录失败', async () => {
    const ok = await useAuthStore.getState().login({ username: 'user', password: 'wrong' });
    expect(ok).toBe(false);
    expect(useAuthStore.getState().error).toBeTruthy();
  });

  it('连续 3 次密码错误后触发账号临时锁定（AUTH_LOGIN_LOCKED）', async () => {
    for (let i = 0; i < 3; i += 1) {
      await useAuthStore.getState().login({ username: 'user', password: 'wrong' });
    }
    // 第 4 次即便密码正确也会因锁定而失败
    const ok = await useAuthStore.getState().login({ username: 'user', password: '123456' });
    expect(ok).toBe(false);
    expect(useAuthStore.getState().error).toContain('锁定');
  });

  it('登出后清空 Token 与所有业务 Store（无跨账号缓存）', async () => {
    await useAuthStore.getState().login({ username: 'user', password: '123456' });
    await usePermissionStore.getState().load();
    // 制造一些 chat 状态
    useChatStore.setState({ messages: [
      { message_id: 'x', conversation_id: 'c', role: 'user', content: 'hi', status: 'done', created_at: '' },
    ] });

    await useAuthStore.getState().logout();

    expect(tokenStore.getAccess()).toBeNull();
    expect(useAuthStore.getState().authenticated).toBe(false);
    expect(usePermissionStore.getState().summary).toBeNull();
    expect(useChatStore.getState().messages).toHaveLength(0);
  });
});

// 验证成员4新增的 PasswordResetRequest 接口在 Mock 下的行为
describe('authMock 密码重置（成员4 /auth/reset-password）', () => {
  beforeEach(() => {
    authMock.resetForTest();
  });

  it('合法的新密码可重置成功（且失败计数归零）', async () => {
    await expect(authMock.resetPassword({ username: 'user', new_password: 'newPass1' }))
      .resolves.toBeUndefined();
    // 验证重置后用新密码可登录（mock 登录返回 ApiResponse<LoginPayload>）
    const resp = await authMock.login({ username: 'user', password: 'newPass1' });
    expect(resp.success).toBe(true);
    expect(resp.data?.tokens.access_token).toBeTruthy();
  });

  it('过短的密码被拒绝', async () => {
    await expect(authMock.resetPassword({ username: 'user', new_password: '123' }))
      .rejects.toMatchObject({ code: ErrorCode.SERVER_ERROR });
  });

  it('不存在的用户被拒绝', async () => {
    await expect(authMock.resetPassword({ username: 'no-such-user', new_password: 'newPass1' }))
      .rejects.toMatchObject({ code: ErrorCode.UNAUTHORIZED });
  });
});
