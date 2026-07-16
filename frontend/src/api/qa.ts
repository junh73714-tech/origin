/**
 * 问答相关 API
 */
import { api } from './request';

// ============ 标准问答 ============
export interface StandardQA {
  id: string;
  knowledge_base_id: string;
  question: string;
  answer: string;
  keywords?: string[];
  category?: string;
  status: string;
  priority: number;
  view_count: number;
  use_count: number;
  published_at?: string;
  expired_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateQARequest {
  knowledge_base_id: string;
  question: string;
  answer: string;
  keywords?: string[];
  category?: string;
  priority?: number;
}

// ============ 会话消息 ============
export interface Conversation {
  id: string;
  user_id: string;
  session_id?: string;
  title?: string;
  status: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  matched_qa_id?: string;
  confidence?: number;
  references?: any[];
  feedback?: string;
  created_at: string;
}

export interface SendMessageRequest {
  conversation_id?: string;
  content: string;
}

export interface SendMessageResponse {
  conversation_id: string;
  message: Message;
  references?: any[];
}

export const qaApi = {
  // ============ 标准问答 ============
  // 获取标准问答列表
  listQA: (params?: { page?: number; page_size?: number; status?: string; category?: string }) =>
    api.get<{ data: { items: StandardQA[]; total: number } }>('/qa/standard', params),

  // 获取标准问答详情
  getQA: (id: string) => api.get<{ data: StandardQA }>(`/qa/standard/${id}`),

  // 创建标准问答
  createQA: (data: CreateQARequest) => api.post<{ data: StandardQA }>('/qa/standard', data),

  // 更新标准问答
  updateQA: (id: string, data: Partial<CreateQARequest>) =>
    api.put<{ data: StandardQA }>(`/qa/standard/${id}`, data),

  // 发布标准问答
  publishQA: (id: string) => api.post(`/qa/standard/${id}/publish`),

  // 下线标准问答
  unpublishQA: (id: string, reason?: string) =>
    api.post(`/qa/standard/${id}/unpublish`, { reason }),

  // 删除标准问答
  deleteQA: (id: string) => api.delete(`/qa/standard/${id}`),

  // ============ 对话 ============
  // 获取会话列表
  listConversations: (params?: { page?: number; page_size?: number }) =>
    api.get<{ data: { items: Conversation[]; total: number } }>('/qa/conversations', params),

  // 获取会话详情
  getConversation: (id: string) =>
    api.get<{ data: { conversation: Conversation; messages: Message[] } }>(
      `/qa/conversations/${id}`
    ),

  // 发送消息
  sendMessage: (data: SendMessageRequest) =>
    api.post<{ data: SendMessageResponse }>('/qa/chat', data),

  // ============ 候选问答 ============
  // 获取候选问答列表
  listCandidates: (params?: { page?: number; page_size?: number; status?: string }) =>
    api.get<{ data: { items: any[]; total: number } }>('/qa/candidates', params),

  // 审核候选问答
  reviewCandidate: (id: string, action: 'approve' | 'reject', comment?: string) =>
    api.post(`/qa/candidates/${id}/review`, { action, comment }),
};
