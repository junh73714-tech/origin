import { describe, it, expect } from 'vitest';
import { useAuthStore } from '@/store/auth';

describe('Auth Store', () => {
  it('should have initial state', () => {
    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('should set auth data', () => {
    const mockUser = {
      id: '1',
      email: 'test@example.com',
      username: 'testuser',
      is_active: true,
      is_superuser: false,
      created_at: '2024-01-01',
      updated_at: '2024-01-01',
    };

    useAuthStore.getState().setAuth(mockUser, 'token123', 'refresh123');

    const state = useAuthStore.getState();
    expect(state.user).toEqual(mockUser);
    expect(state.accessToken).toBe('token123');
    expect(state.refreshToken).toBe('refresh123');
    expect(state.isAuthenticated).toBe(true);
  });

  it('should logout', () => {
    useAuthStore.getState().logout();

    const state = useAuthStore.getState();
    expect(state.user).toBeNull();
    expect(state.accessToken).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });
});
