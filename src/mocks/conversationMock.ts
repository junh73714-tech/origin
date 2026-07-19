// 会话与引用 Mock（对齐成员6契约）。内存态，用于独立自测。
import type { PageQuery, PageResult } from '@/types/common';
import { ErrorCode } from '@/types/common';
import type { ApiError } from '@/types/common';
import type {
  CitationDetail,
  Conversation,
  ConversationDetail,
  ChatMessage,
} from '@/types/chat';

let seq = 100;
function nextId(prefix: string): string {
  seq += 1;
  return `${prefix}-${seq}`;
}

function delay<T>(value: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

const conversations: Conversation[] = [
  {
    conversation_id: 'c-001',
    title: '如何重置账号密码',
    updated_at: '2026-07-15T09:20:00Z',
    archived: false,
    message_count: 4,
  },
  {
    conversation_id: 'c-002',
    title: '产品导出功能说明',
    updated_at: '2026-07-14T16:05:00Z',
    archived: false,
    message_count: 2,
  },
  {
    conversation_id: 'c-003',
    title: '历史归档会话示例',
    updated_at: '2026-07-10T11:00:00Z',
    archived: true,
    message_count: 6,
  },
];

const messagesByConv: Record<string, ChatMessage[]> = {
  'c-001': [
    {
      message_id: 'm-001',
      conversation_id: 'c-001',
      role: 'user',
      content: '如何重置账号密码？',
      status: 'done',
      created_at: '2026-07-15T09:19:00Z',
    },
    {
      message_id: 'm-002',
      conversation_id: 'c-001',
      role: 'assistant',
      content:
        '可在登录页点击“忘记密码”，通过绑定邮箱接收重置链接完成密码重置。企业统一身份用户请通过内部门户重置。',
      status: 'done',
      answer_type: 'standard_qa',
      evidence_status: 'sufficient',
      citations: [
        { citation_id: 'cite-001', index: 1, document_name: '产品使用手册', snippet: '密码重置流程' },
      ],
      created_at: '2026-07-15T09:20:00Z',
    },
  ],
};

const citationDetails: Record<string, CitationDetail> = {
  'cite-001': {
    citation_id: 'cite-001',
    document_name: '产品使用手册',
    title_path: ['账号管理', '密码与安全', '重置密码'],
    page_no: 12,
    quoted_text:
      '用户可在登录页点击“忘记密码”，系统将向绑定邮箱发送一次性重置链接，链接有效期为 30 分钟。',
    document_version: 'v2.3',
    effective_time: '2026-06-01T00:00:00Z',
    source_type: '正式发布文档',
    can_open_source: true,
    source_url: 'https://docs.example.com/manual/reset-password',
  },
  // 无权限引用示例：后端返回 access_denied，前端不得展示真实地址与正文
  'cite-restricted': {
    citation_id: 'cite-restricted',
    document_name: '内部运维手册（受限）',
    title_path: [],
    quoted_text: '',
    document_version: '',
    effective_time: '',
    source_type: '受限文档',
    can_open_source: false,
    access_denied: true,
  },
};

export function getCitationDetailSync(id: string): CitationDetail | undefined {
  return citationDetails[id];
}

export const conversationMock = {
  async list(query: PageQuery): Promise<PageResult<Conversation>> {
    const kw = query.keyword?.trim();
    const filtered = kw
      ? conversations.filter((c) => c.title.includes(kw))
      : conversations;
    const start = (query.page - 1) * query.page_size;
    const items = filtered.slice(start, start + query.page_size);
    return delay({
      items,
      total: filtered.length,
      page: query.page,
      page_size: query.page_size,
    });
  },

  async create(title?: string): Promise<Conversation> {
    const conv: Conversation = {
      conversation_id: nextId('c'),
      title: title || '新会话',
      updated_at: new Date().toISOString(),
      archived: false,
      message_count: 0,
    };
    conversations.unshift(conv);
    messagesByConv[conv.conversation_id] = [];
    return delay(conv, 150);
  },

  async detail(conversationId: string): Promise<ConversationDetail> {
    const conv = conversations.find((c) => c.conversation_id === conversationId);
    if (!conv) {
      const err: ApiError = { code: 'NOT_FOUND', message: '会话不存在或已被删除。' };
      return Promise.reject(err);
    }
    return delay({ ...conv, messages: messagesByConv[conversationId] ?? [] });
  },

  async rename(conversationId: string, title: string): Promise<void> {
    const conv = conversations.find((c) => c.conversation_id === conversationId);
    if (conv) conv.title = title;
    return delay(undefined as void, 120);
  },

  async remove(conversationId: string): Promise<void> {
    const idx = conversations.findIndex((c) => c.conversation_id === conversationId);
    if (idx >= 0) conversations.splice(idx, 1);
    delete messagesByConv[conversationId];
    return delay(undefined as void, 120);
  },

  async archive(conversationId: string, archived: boolean): Promise<void> {
    const conv = conversations.find((c) => c.conversation_id === conversationId);
    if (conv) conv.archived = archived;
    return delay(undefined as void, 120);
  },

  async stop(_conversationId: string, _messageId: string): Promise<void> {
    return delay(undefined as void, 60);
  },

  async citationDetail(citationId: string): Promise<CitationDetail> {
    const detail = citationDetails[citationId];
    if (!detail) {
      const err: ApiError = { code: ErrorCode.SERVER_ERROR, message: '引用详情获取失败。' };
      return Promise.reject(err);
    }
    return delay(detail, 200);
  },
};
