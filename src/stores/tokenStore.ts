// 令牌保管：仅存于内存，绝不写入 LocalStorage，避免持久化敏感信息。
// 页面刷新后需重新登录，这是安全上的有意取舍。
import type { TokenPair } from '@/types/auth';

let accessToken: string | null = null;
let refreshToken: string | null = null;

export const tokenStore = {
  set(pair: TokenPair): void {
    accessToken = pair.access_token;
    refreshToken = pair.refresh_token;
  },
  getAccess(): string | null {
    return accessToken;
  },
  getRefresh(): string | null {
    return refreshToken;
  },
  clear(): void {
    accessToken = null;
    refreshToken = null;
  },
};
