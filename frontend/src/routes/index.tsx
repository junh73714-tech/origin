/**
 * 前端路由配置
 * 成员3：管理后台前端 - 路由集成
 * 包含用户端路由和管理后台路由
 */
import type { RouteObject } from 'react-router-dom';

// 用户端布局
import { Layout } from '@/layouts';
// 管理后台布局
import { AdminLayout } from '@/layouts';

// 管理后台页面
import {
  Dashboard,
  // 用户与组织
  UserManage,
  DepartmentManage,
  UserGroupManage,
  RoleManage,
  TempAuthManage,
  // 权限中心
  PermissionManage,
  DataPermissionManage,
  KBAuthManage,
  DocClassification,
  PermissionRules,
  PermissionAudit,
  // 知识库与文档
  AdminKBList,
  AdminDocList,
  DocVersionManage,
  ChunkView,
  IndexTaskManage,
  // 问答优化
  CandidateQA,
  PendingReview,
  StandardQA,
  SimilarQuestions,
  FrequentQuestions,
  UnmatchedQuestions,
  LowQualityAnswers,
  // 检索调试
  SearchDebug,
  // 评估中心
  EvalDatasets,
  EvalSamples,
  EvalTasks,
  EvalHistory,
  EvalCompare,
  // 安全与审计
  QueryLogs,
  OperationLogs,
  LoginLogs,
  SecurityEvents,
  RiskAlerts,
  // 系统设置
  LLMConfig,
  EmbeddingConfig,
  RerankerConfig,
  OCRConfig,
  RetrievalConfig,
  PromptTemplates,
  SystemHealth,
} from '@/pages/admin';

/** 路由配置 */
export const routes: RouteObject[] = [
  // ========== 用户端路由 ==========
  {
    element: <Layout />,
    children: [
      {
        path: '/',
        lazy: () => import('@/pages/user/Home'),
      },
      {
        path: '/home',
        lazy: () => import('@/pages/user/Home'),
      },
      {
        path: '/chat',
        lazy: () => import('@/pages/user/Chat'),
      },
      {
        path: '/chat/:conversationId',
        lazy: () => import('@/pages/user/Chat'),
      },
      {
        path: '/history',
        lazy: () => import('@/pages/user/History'),
      },
      {
        path: '/knowledge-bases',
        lazy: () => import('@/pages/user/KnowledgeBaseList'),
      },
      {
        path: '/knowledge-bases/:kbId/documents',
        lazy: () => import('@/pages/user/DocumentList'),
      },
      {
        path: '/qa',
        lazy: () => import('@/pages/user/QAList'),
      },
    ],
  },

  // ========== 管理后台路由 ==========
  {
    path: '/admin',
    element: <AdminLayout />,
    children: [
      // 工作台
      { index: true, element: <Dashboard /> },
      { path: 'dashboard', element: <Dashboard /> },

      // 用户与组织
      { path: 'users', element: <UserManage /> },
      { path: 'departments', element: <DepartmentManage /> },
      { path: 'user-groups', element: <UserGroupManage /> },
      { path: 'roles', element: <RoleManage /> },
      { path: 'temp-auth', element: <TempAuthManage /> },

      // 权限中心
      { path: 'permissions', element: <PermissionManage /> },
      { path: 'data-permissions', element: <DataPermissionManage /> },
      { path: 'kb-auth', element: <KBAuthManage /> },
      { path: 'doc-classification', element: <DocClassification /> },
      { path: 'permission-rules', element: <PermissionRules /> },
      { path: 'permission-audit', element: <PermissionAudit /> },

      // 知识库与文档
      { path: 'knowledge-bases', element: <AdminKBList /> },
      { path: 'documents', element: <AdminDocList /> },
      { path: 'document-versions', element: <DocVersionManage /> },
      { path: 'chunks', element: <ChunkView /> },
      { path: 'index-tasks', element: <IndexTaskManage /> },

      // 问答优化
      { path: 'candidate-qa', element: <CandidateQA /> },
      { path: 'pending-review', element: <PendingReview /> },
      { path: 'standard-qa', element: <StandardQA /> },
      { path: 'similar-questions', element: <SimilarQuestions /> },
      { path: 'frequent-questions', element: <FrequentQuestions /> },
      { path: 'unmatched-questions', element: <UnmatchedQuestions /> },
      { path: 'low-quality-answers', element: <LowQualityAnswers /> },

      // 检索调试
      { path: 'search-debug', element: <SearchDebug /> },

      // 评估中心
      { path: 'evaluation/datasets', element: <EvalDatasets /> },
      { path: 'evaluation/samples', element: <EvalSamples /> },
      { path: 'evaluation/tasks', element: <EvalTasks /> },
      { path: 'evaluation/history', element: <EvalHistory /> },
      { path: 'evaluation/compare', element: <EvalCompare /> },

      // 安全与审计
      { path: 'logs/query', element: <QueryLogs /> },
      { path: 'logs/operation', element: <OperationLogs /> },
      { path: 'logs/login', element: <LoginLogs /> },
      { path: 'security/events', element: <SecurityEvents /> },
      { path: 'security/alerts', element: <RiskAlerts /> },

      // 系统设置
      { path: 'settings/llm', element: <LLMConfig /> },
      { path: 'settings/embedding', element: <EmbeddingConfig /> },
      { path: 'settings/reranker', element: <RerankerConfig /> },
      { path: 'settings/ocr', element: <OCRConfig /> },
      { path: 'settings/retrieval', element: <RetrievalConfig /> },
      { path: 'settings/prompts', element: <PromptTemplates /> },
      { path: 'settings/health', element: <SystemHealth /> },
    ],
  },

  // ========== 认证路由 ==========
  {
    path: '/login',
    lazy: () => import('@/pages/auth/Login'),
  },

  // ========== 404 ==========
  {
    path: '*',
    element: (
      <div style={{ textAlign: 'center', padding: '100px 20px' }}>
        <h1>404</h1>
        <p>页面不存在</p>
      </div>
    ),
  },
];