/**
 * MSW 请求处理器 - 完整的 Mock API
 * 支持前端在无后端情况下开发
 */
import { http, HttpResponse, delay } from 'msw';

// 模拟延迟（可选，模拟真实网络）
const SIMULATE_DELAY = 200;

// ============ 认证相关 ============
export const authHandlers = [
  // 登录
  http.post('/api/v1/auth/login', async ({ request }) => {
    await delay(SIMULATE_DELAY);
    const body = await request.json() as { username: string; password: string };

    if (body.username === 'test' && body.password === 'password') {
      return HttpResponse.json({
        success: true,
        data: {
          user: {
            id: 'usr_01HXYZ1234567890',
            email: 'test@example.com',
            username: 'test',
            full_name: 'Test User',
            is_active: true,
            is_superuser: false,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
          },
          tokens: {
            access_token: 'mock-access-token-xxx',
            refresh_token: 'mock-refresh-token-xxx',
            token_type: 'bearer',
            expires_in: 1800,
          },
        },
      });
    }

    return HttpResponse.json(
      {
        success: false,
        error: {
          code: 'AUTH_INVALID_CREDENTIALS',
          message: '用户名或密码错误',
        },
      },
      { status: 401 }
    );
  }),

  // 注册
  http.post('/api/v1/auth/register', async ({ request }) => {
    await delay(SIMULATE_DELAY);
    const body = await request.json() as { email: string; username: string; password: string };

    return HttpResponse.json({
      success: true,
      data: {
        id: 'usr_01HXYZ1234567890',
        email: body.email,
        username: body.username,
        full_name: null,
        is_active: true,
        is_superuser: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });
  }),

  // 刷新令牌
  http.post('/api/v1/auth/refresh', async ({ request }) => {
    await delay(SIMULATE_DELAY);
    return HttpResponse.json({
      success: true,
      data: {
        access_token: 'mock-access-token-refreshed',
        refresh_token: 'mock-refresh-token-refreshed',
        token_type: 'bearer',
        expires_in: 1800,
      },
    });
  }),

  // 登出
  http.post('/api/v1/auth/logout', async () => {
    await delay(SIMULATE_DELAY);
    return HttpResponse.json({ success: true });
  }),

  // 获取当前用户
  http.get('/api/v1/auth/me', () => {
    return HttpResponse.json({
      success: true,
      data: {
        id: 'usr_01HXYZ1234567890',
        email: 'test@example.com',
        username: 'test',
        full_name: 'Test User',
        is_active: true,
        is_superuser: false,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    });
  }),
];

// ============ 知识库相关 ============
export const knowledgeBaseHandlers = [
  // 获取知识库列表
  http.get('/api/v1/knowledge-bases', async ({ request }) => {
    await delay(SIMULATE_DELAY);
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const pageSize = parseInt(url.searchParams.get('page_size') || '20');

    const mockData = [
      {
        id: 'kb_01HXYZ1000000000',
        name: '产品知识库',
        description: '产品相关文档和手册',
        icon: null,
        is_public: false,
        settings: {},
        document_count: 15,
        created_at: '2024-01-15T00:00:00Z',
        updated_at: '2024-01-20T00:00:00Z',
      },
      {
        id: 'kb_01HXYZ1000000001',
        name: '技术文档',
        description: '技术架构和开发文档',
        icon: null,
        is_public: false,
        settings: {},
        document_count: 8,
        created_at: '2024-01-10T00:00:00Z',
        updated_at: '2024-01-18T00:00:00Z',
      },
      {
        id: 'kb_01HXYZ1000000002',
        name: 'FAQ',
        description: '常见问题解答',
        icon: null,
        is_public: true,
        settings: {},
        document_count: 25,
        created_at: '2024-01-05T00:00:00Z',
        updated_at: '2024-01-25T00:00:00Z',
      },
    ];

    const start = (page - 1) * pageSize;
    const items = mockData.slice(start, start + pageSize);

    return HttpResponse.json({
      success: true,
      data: {
        items,
        total: mockData.length,
        page,
        page_size: pageSize,
        total_pages: Math.ceil(mockData.length / pageSize),
      },
    });
  }),

  // 获取知识库详情
  http.get('/api/v1/knowledge-bases/:id', ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: {
        id: params.id,
        name: '产品知识库',
        description: '产品相关文档和手册',
        icon: null,
        is_public: false,
        settings: {},
        document_count: 15,
        created_at: '2024-01-15T00:00:00Z',
        updated_at: '2024-01-20T00:00:00Z',
      },
    });
  }),

  // 创建知识库
  http.post('/api/v1/knowledge-bases', async ({ request }) => {
    await delay(SIMULATE_DELAY);
    const body = await request.json() as any;
    return HttpResponse.json({
      success: true,
      data: {
        id: `kb_${Date.now()}`,
        name: body.name,
        description: body.description,
        is_public: body.is_public || false,
        document_count: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    });
  }),

  // 更新知识库
  http.put('/api/v1/knowledge-bases/:id', async ({ request, params }) => {
    await delay(SIMULATE_DELAY);
    const body = await request.json() as any;
    return HttpResponse.json({
      success: true,
      data: {
        id: params.id,
        ...body,
        updated_at: new Date().toISOString(),
      },
    });
  }),

  // 删除知识库
  http.delete('/api/v1/knowledge-bases/:id', () => {
    return HttpResponse.json({ success: true });
  }),
];

// ============ 文档相关 ============
export const documentHandlers = [
  // 获取文档列表
  http.get('/api/v1/knowledge-bases/:kbId/documents', async ({ request, params }) => {
    await delay(SIMULATE_DELAY);
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');

    const mockDocs = [
      {
        id: 'doc_01HXYZ2000000000',
        knowledge_base_id: params.kbId,
        name: '产品介绍.pdf',
        file_type: 'pdf',
        file_size: 1024000,
        status: 'completed',
        char_count: 5000,
        current_version: 1,
        created_at: '2024-01-16T00:00:00Z',
        updated_at: '2024-01-16T00:00:00Z',
      },
      {
        id: 'doc_01HXYZ2000000001',
        knowledge_base_id: params.kbId,
        name: '用户手册.docx',
        file_type: 'docx',
        file_size: 512000,
        status: 'completed',
        char_count: 3000,
        current_version: 2,
        created_at: '2024-01-17T00:00:00Z',
        updated_at: '2024-01-19T00:00:00Z',
      },
    ];

    return HttpResponse.json({
      success: true,
      data: {
        items: mockDocs,
        total: mockDocs.length,
        page,
        page_size: 20,
        total_pages: 1,
      },
    });
  }),

  // 获取文档详情
  http.get('/api/v1/documents/:id', ({ params }) => {
    return HttpResponse.json({
      success: true,
      data: {
        id: params.id,
        knowledge_base_id: 'kb_01HXYZ1000000000',
        name: '产品介绍.pdf',
        file_type: 'pdf',
        file_size: 1024000,
        status: 'completed',
        char_count: 5000,
        current_version: 1,
        created_at: '2024-01-16T00:00:00Z',
        updated_at: '2024-01-16T00:00:00Z',
      },
    });
  }),

  // 上传文档
  http.post('/api/v1/knowledge-bases/:kbId/documents/upload', async () => {
    await delay(500);
    return HttpResponse.json({
      success: true,
      data: {
        document_id: `doc_${Date.now()}`,
        name: 'uploaded_file.pdf',
        file_type: 'pdf',
        file_size: 1024000,
        status: 'pending',
      },
    });
  }),

  // 删除文档
  http.delete('/api/v1/documents/:id', () => {
    return HttpResponse.json({ success: true });
  }),
];

// ============ 问答相关 ============
export const qaHandlers = [
  // 发送消息
  http.post('/api/v1/qa/chat', async ({ request }) => {
    await delay(1000);
    const body = await request.json() as { content: string; conversation_id?: string };

    return HttpResponse.json({
      success: true,
      data: {
        conversation_id: body.conversation_id || `cnv_${Date.now()}`,
        message: {
          id: `msg_${Date.now()}`,
          conversation_id: body.conversation_id || `cnv_${Date.now()}`,
          role: 'assistant',
          content: `这是 Mock 回答。您的问题是：${body.content}`,
          created_at: new Date().toISOString(),
        },
        references: [
          {
            chunk_id: 'chunk_001',
            content: '相关文档内容片段...',
            document_name: '产品介绍.pdf',
            score: 0.95,
          },
        ],
      },
    });
  }),

  // 获取标准问答列表
  http.get('/api/v1/qa/standard', async ({ request }) => {
    await delay(SIMULATE_DELAY);
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');

    const mockQAs = [
      {
        id: 'qa_01HXYZ3000000000',
        knowledge_base_id: 'kb_01HXYZ1000000000',
        question: '如何注册账号？',
        answer: '点击页面右上角的注册按钮，填写邮箱和密码即可完成注册。',
        keywords: ['注册', '账号', '新用户'],
        category: '用户指南',
        status: 'published',
        priority: 10,
        view_count: 150,
        use_count: 45,
        created_at: '2024-01-15T00:00:00Z',
        updated_at: '2024-01-20T00:00:00Z',
      },
      {
        id: 'qa_01HXYZ3000000001',
        knowledge_base_id: 'kb_01HXYZ1000000000',
        question: '如何重置密码？',
        answer: '在登录页面点击忘记密码链接，输入您的注册邮箱，我们会发送重置链接。',
        keywords: ['密码', '重置', '忘记'],
        category: '用户指南',
        status: 'published',
        priority: 8,
        view_count: 120,
        use_count: 38,
        created_at: '2024-01-15T00:00:00Z',
        updated_at: '2024-01-20T00:00:00Z',
      },
    ];

    return HttpResponse.json({
      success: true,
      data: {
        items: mockQAs,
        total: mockQAs.length,
        page,
        page_size: 20,
        total_pages: 1,
      },
    });
  }),

  // 获取会话列表
  http.get('/api/v1/qa/conversations', async () => {
    await delay(SIMULATE_DELAY);
    return HttpResponse.json({
      success: true,
      data: {
        items: [
          {
            id: 'cnv_01HXYZ4000000000',
            user_id: 'usr_01HXYZ1234567890',
            title: '关于产品的问题',
            status: 'active',
            message_count: 5,
            created_at: '2024-01-20T10:00:00Z',
            updated_at: '2024-01-20T10:30:00Z',
          },
        ],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    });
  }),
];

// ============ 反馈相关 ============
export const feedbackHandlers = [
  // 提交反馈
  http.post('/api/v1/feedback', async ({ request }) => {
    await delay(SIMULATE_DELAY);
    const body = await request.json() as any;
    return HttpResponse.json({
      success: true,
      data: {
        id: `fb_${Date.now()}`,
        message_id: body.message_id,
        feedback: body.feedback,
        comment: body.comment,
        score: body.score,
        created_at: new Date().toISOString(),
      },
    });
  }),
];

// ============ 健康检查 ============
export const healthHandlers = [
  http.get('/api/v1/health', () => {
    return HttpResponse.json({
      success: true,
      data: {
        status: 'healthy',
        version: '0.1.0',
        timestamp: new Date().toISOString(),
        services: {
          database: { status: 'healthy' },
          redis: { status: 'healthy' },
          minio: { status: 'healthy' },
        },
      },
    });
  }),

  http.get('/api/v1/ready', () => {
    return HttpResponse.json({
      success: true,
      data: { ready: true },
    });
  }),

  http.get('/api/v1/live', () => {
    return HttpResponse.json({
      success: true,
      data: { alive: true },
    });
  }),
];

// 合并所有 handlers
export const handlers = [
  ...healthHandlers,
  ...authHandlers,
  ...knowledgeBaseHandlers,
  ...documentHandlers,
  ...qaHandlers,
  ...feedbackHandlers,
];
