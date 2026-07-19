// 全局重置协调器：切换/退出用户时统一清空所有 Store，杜绝跨账号缓存。
// 各 Store 在创建时注册自己的 reset 方法。
type ResetFn = () => void;

const resetFns = new Set<ResetFn>();

export function registerReset(fn: ResetFn): void {
  resetFns.add(fn);
}

export function resetAllStores(): void {
  resetFns.forEach((fn) => fn());
}
