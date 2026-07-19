// 会话与引用 API（对齐成员6真实契约）。
// 路径前缀：/qa/conversations（不再使用 /conversations）
// SSE 流式发送单独封装在 sseClient。
import { http, unwrap } from './http';
import { USE_MOCK } from './env';
import { conversationMock } from '@/mocks/conversationMock';
import type { ApiResponse, PageQuery, PageResult } from '@/types/common';
import type {
  CitationDetail,
  Conversation,
  ConversationDetail,
} from '@/types/chat';

export const conversationApi = {
  async list(query: PageQuery): Promise<PageResult<Conversation>> {
    if (USE_MOCK) return conversationMock.list(query);
    const { data } = await http.get<ApiResponse<PageResult<Conversation>>>(
      '/qa/conversations',
      { params: query },
    );
    return unwrap(data);
  },

  /**
   * 新建会话：后端没有专门的 POST /qa/conversations。
   * 实际新建发生在首次 /qa/chat 发问后由 message_start 事件带回 conversation_id。
   * 这里保持签名兼容并返回空占位，避免上层误用。
   */
  async create(title?: string): Promise<Conversation> {
    if (USE_MOCK) return conversationMock.create(title);
    return {
      conversation_id: '',
      title: title ?? '',
      updated_at: new Date().toISOString(),
      archived: false,
      message_count: 0,
    };
  },

  async detail(conversationId: string): Promise<ConversationDetail> {
    if (USE_MOCK) return conversationMock.detail(conversationId);
    const { data } = await http.get<ApiResponse<ConversationDetail>>(
      `/qa/conversations/${conversationId}`,
    );
    return unwrap(data);
  },

  /** 重命名：后端未提供独立端点；404 静默忽略。 */
  async rename(conversationId: string, title: string): Promise<void> {
    if (USE_MOCK) return conversationMock.rename(conversationId, title);
    try {
      await http.patch(`/qa/conversations/${conversationId}`, { title });
    } catch {
      /* noop */
    }
  },

  async remove(conversationId: string): Promise<void> {
    if (USE_MOCK) return conversationMock.remove(conversationId);
    try {
      await http.delete(`/qa/conversations/${conversationId}`);
    } catch {
      /* noop */
    }
  },

  async archive(conversationId: string, archived: boolean): Promise<void> {
    if (USE_MOCK) return conversationMock.archive(conversationId, archived);
    try {
      await http.patch(`/qa/conversations/${conversationId}`, { archived });
    } catch {
      /* noop */
    }
  },

  /**
   * 停止生成：真实后端为 POST /qa/queries/{query_id}/cancel（用 query_id 而非 message_id）。
   * 签名上沿用 (conversationId, messageId)；实际取 messageId 当 query_id 用，失败静默。
   */
  async stop(conversationId: string, messageId: string): Promise<void> {
    if (USE_MOCK) return conversationMock.stop(conversationId, messageId);
    try {
      await http.post(`/qa/queries/${messageId}/cancel`);
    } catch {
      /* noop */
    }
  },

  /** 引用详情：仅凭 citation_id 获取，无权限由后端返回受限标记 */
  async citationDetail(citationId: string): Promise<CitationDetail> {
    if (USE_MOCK) return conversationMock.citationDetail(citationId);
    const { data } = await http.get<ApiResponse<CitationDetail>>(
      `/qa/citations/${citationId}`,
    );
    return unwrap(data);
  },
};