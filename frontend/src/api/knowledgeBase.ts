/**
 * 知识库相关 API
 */
import { api } from './request';

export interface KnowledgeBase {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  is_public: boolean;
  settings?: Record<string, any>;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface CreateKnowledgeBaseRequest {
  name: string;
  description?: string;
  icon?: string;
  is_public?: boolean;
  settings?: Record<string, any>;
}

export interface UpdateKnowledgeBaseRequest {
  name?: string;
  description?: string;
  icon?: string;
  is_public?: boolean;
  settings?: Record<string, any>;
}

export const knowledgeBaseApi = {
  // 获取知识库列表
  list: (params?: { page?: number; page_size?: number; keyword?: string }) =>
    api.get<{ data: { items: KnowledgeBase[]; total: number } }>('/knowledge-bases', params),

  // 获取知识库详情
  get: (id: string) => api.get<{ data: KnowledgeBase }>(`/knowledge-bases/${id}`),

  // 创建知识库
  create: (data: CreateKnowledgeBaseRequest) =>
    api.post<{ data: KnowledgeBase }>('/knowledge-bases', data),

  // 更新知识库
  update: (id: string, data: UpdateKnowledgeBaseRequest) =>
    api.put<{ data: KnowledgeBase }>(`/knowledge-bases/${id}`, data),

  // 删除知识库
  delete: (id: string) => api.delete(`/knowledge-bases/${id}`),

  // 获取知识库统计
  getStats: (id: string) =>
    api.get<{ data: { document_count: number; chunk_count: number; qa_count: number } }>(
      `/knowledge-bases/${id}/stats`
    ),
};
