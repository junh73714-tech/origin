/**
 * 文档相关 API
 */
import { api } from './request';

export interface Document {
  id: string;
  knowledge_base_id: string;
  name: string;
  file_type: string;
  file_size: number;
  status: string;
  char_count?: number;
  current_version: number;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface UploadDocumentResponse {
  document_id: string;
  name: string;
  file_type: string;
  file_size: number;
  status: string;
}

export const documentApi = {
  // 获取文档列表
  list: (kbId: string, params?: { page?: number; page_size?: number }) =>
    api.get<{ data: { items: Document[]; total: number } }>(
      `/knowledge-bases/${kbId}/documents`,
      params
    ),

  // 获取文档详情
  get: (documentId: string) => api.get<{ data: Document }>(`/documents/${documentId}`),

  // 上传文档
  upload: (
    kbId: string,
    file: File,
    onProgress?: (percent: number) => void
  ) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.upload<{ data: UploadDocumentResponse }>(
      `/knowledge-bases/${kbId}/documents/upload`,
      formData,
      onProgress
    );
  },

  // 删除文档
  delete: (documentId: string) => api.delete(`/documents/${documentId}`),

  // 获取文档版本列表
  getVersions: (documentId: string) =>
    api.get<{ data: any[] }>(`/documents/${documentId}/versions`),

  // 获取文档 Chunk 列表
  getChunks: (documentId: string, params?: { page?: number; page_size?: number }) =>
    api.get<{ data: { items: any[]; total: number } }>(
      `/documents/${documentId}/chunks`,
      params
    ),
};
