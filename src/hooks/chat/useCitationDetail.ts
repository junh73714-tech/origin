// hooks/chat：封装引用详情的加载逻辑，供引用抽屉使用。
// 无权限（access_denied）时不保留旧的敏感内容。
import { useCallback, useEffect, useState } from 'react';
import { conversationApi } from '@/api/conversationApi';
import type { CitationDetail } from '@/types/chat';
import type { ApiError } from '@/types/common';

interface UseCitationResult {
  detail: CitationDetail | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useCitationDetail(
  citationId: string | null,
): UseCitationResult {
  const [detail, setDetail] = useState<CitationDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!citationId) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError(null);
    setDetail(null); // 先清空，避免残留上一个引用的敏感内容
    try {
      const data = await conversationApi.citationDetail(citationId);
      setDetail(data);
    } catch (e) {
      setError((e as ApiError).message || '引用详情获取失败。');
    } finally {
      setLoading(false);
    }
  }, [citationId]);

  useEffect(() => {
    load();
  }, [load]);

  return { detail, loading, error, reload: load };
}
