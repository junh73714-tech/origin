/**
 * 管理后台 Hooks
 * 成员3：管理后台前端
 * 管理后台专用的自定义 Hook
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { message } from 'antd';
import type { AdminPaginationParams, AdminFilterParams, AdminSortParams } from '@/types/admin';

/**
 * 分页 Hook
 * 管理后台列表页面的分页、排序、筛选状态管理
 */
export function usePagination(initialPageSize = 20) {
  const [pagination, setPagination] = useState<AdminPaginationParams>({
    page: 1,
    page_size: initialPageSize,
  });
  const [sort, setSort] = useState<AdminSortParams>({});
  const [filters, setFilters] = useState<AdminFilterParams>({});

  /** 页码变更 */
  const handlePageChange = useCallback((page: number, pageSize: number) => {
    setPagination({ page, page_size: pageSize });
  }, []);

  /** 排序变更 */
  const handleSortChange = useCallback((sortBy?: string, sortOrder?: 'asc' | 'desc') => {
    setSort({ sort_by: sortBy, sort_order: sortOrder });
    // 排序时重置到第一页
    setPagination((prev) => ({ ...prev, page: 1 }));
  }, []);

  /** 筛选变更 */
  const handleFilterChange = useCallback((key: string, value: unknown) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  /** 搜索 */
  const handleSearch = useCallback(() => {
    setPagination((prev) => ({ ...prev, page: 1 }));
  }, []);

  /** 重置 */
  const handleReset = useCallback(() => {
    setFilters({});
    setSort({});
    setPagination({ page: 1, page_size: initialPageSize });
  }, [initialPageSize]);

  return {
    pagination,
    sort,
    filters,
    handlePageChange,
    handleSortChange,
    handleFilterChange,
    handleSearch,
    handleReset,
  };
}

/**
 * 异步加载 Hook
 * 管理后台数据加载的通用封装
 */
export function useAsyncData<T>(
  loadFn: () => Promise<T>,
  deps: unknown[] = []
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loadFn();
      setData(result);
    } catch (err) {
      setError(err as Error);
      message.error((err as Error).message || '数据加载失败');
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    load();
  }, [load]);

  return { data, loading, error, reload: load };
}

/**
 * 确认操作 Hook
 * 管理后台高风险操作的确认状态管理
 */
export function useConfirmAction() {
  const [open, setOpen] = useState(false);
  const [confirmLoading, setConfirmLoading] = useState(false);

  /** 打开确认弹窗 */
  const show = useCallback(() => {
    setOpen(true);
  }, []);

  /** 关闭确认弹窗 */
  const hide = useCallback(() => {
    setOpen(false);
    setConfirmLoading(false);
  }, []);

  /** 执行确认操作 */
  const execute = useCallback(async (action: () => Promise<void> | void) => {
    setConfirmLoading(true);
    try {
      await action();
      hide();
      message.success('操作成功');
    } catch (err) {
      message.error((err as Error).message || '操作失败');
    } finally {
      setConfirmLoading(false);
    }
  }, [hide]);

  return { open, confirmLoading, show, hide, execute };
}

/**
 * 轮询 Hook
 * 用于长任务状态轮询
 */
export function usePolling(
  callback: () => Promise<void>,
  interval: number = 5000,
  enabled: boolean = true
) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return;

    const tick = () => {
      savedCallback.current();
    };

    // 立即执行一次
    tick();

    const timer = setInterval(tick, interval);
    return () => clearInterval(timer);
  }, [interval, enabled]);
}

/**
 * 详情抽屉 Hook
 * 管理后台详情抽屉的打开/关闭状态管理
 */
export function useDetailDrawer<T = unknown>() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<T | null>(null);

  /** 打开抽屉并设置数据 */
  const show = useCallback((item: T) => {
    setData(item);
    setOpen(true);
  }, []);

  /** 关闭抽屉 */
  const hide = useCallback(() => {
    setOpen(false);
    // 延迟清空数据，避免关闭动画期间内容消失
    setTimeout(() => setData(null), 300);
  }, []);

  return { open, data, show, hide };
}