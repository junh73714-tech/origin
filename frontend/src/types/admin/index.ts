/**
 * 管理后台类型定义
 * 成员3：管理后台前端 - 类型定义
 */

// ==================== 工作台相关 ====================

/** 工作台概览统计 */
export interface DashboardStats {
  /** 知识库数量 */
  kb_count: number;
  /** 文档总数 */
  document_count: number;
  /** 已发布文档数 */
  published_document_count: number;
  /** 文档处理失败数 */
  failed_document_count: number;
  /** 今日查询量 */
  today_query_count: number;
  /** 标准问答命中率 (0-1) */
  qa_hit_rate: number;
  /** 拒答率 (0-1) */
  rejection_rate: number;
  /** 未命中问题数 */
  unmatched_question_count: number;
  /** 低质量答案数 */
  low_quality_answer_count: number;
  /** 平均响应时间（毫秒） */
  avg_response_time_ms: number;
  /** 风险事件数 */
  risk_event_count: number;
}

/** 时间范围枚举 */
export type TimeRange = 'today' | 'week' | 'month' | 'quarter' | 'year';

// ==================== 用户与组织相关 ====================

/** 用户状态 */
export type UserStatus = 'active' | 'disabled' | 'locked';

/** 用户信息 */
export interface AdminUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  phone?: string;
  department_id?: string;
  department_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  status: UserStatus;
  last_login_at?: string;
  created_at: string;
  updated_at: string;
}

/** 创建用户请求 */
export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
  full_name: string;
  phone?: string;
  department_id?: string;
}

/** 更新用户请求 */
export interface UpdateUserRequest {
  email?: string;
  full_name?: string;
  phone?: string;
  department_id?: string;
  is_active?: boolean;
}

/** 部门信息 */
export interface Department {
  id: string;
  name: string;
  parent_id?: string;
  parent_name?: string;
  manager_id?: string;
  manager_name?: string;
  member_count: number;
  description?: string;
  created_at: string;
  updated_at: string;
}

/** 创建/更新部门请求 */
export interface DepartmentRequest {
  name: string;
  parent_id?: string;
  manager_id?: string;
  description?: string;
}

/** 用户组信息 */
export interface UserGroup {
  id: string;
  name: string;
  description?: string;
  member_count: number;
  created_at: string;
  updated_at: string;
}

/** 创建/更新用户组请求 */
export interface UserGroupRequest {
  name: string;
  description?: string;
}

// ==================== 角色与权限相关 ====================

/** 角色信息 */
export interface Role {
  id: string;
  name: string;
  code: string;
  description?: string;
  is_system: boolean;
  user_count: number;
  permission_count: number;
  created_at: string;
  updated_at: string;
}

/** 创建/更新角色请求 */
export interface RoleRequest {
  name: string;
  code: string;
  description?: string;
  permission_ids?: string[];
}

/** 权限信息 */
export interface Permission {
  id: string;
  name: string;
  code: string;
  resource_type: string;
  action: string;
  description?: string;
}

/** 功能权限分组 */
export interface PermissionGroup {
  resource_type: string;
  resource_label: string;
  permissions: Permission[];
}

/** 数据权限规则 */
export interface DataPermissionRule {
  id: string;
  name: string;
  description?: string;
  target_type: 'user' | 'role' | 'department' | 'user_group';
  target_id: string;
  target_name: string;
  resource_type: string;
  scope_type: 'all' | 'department' | 'self' | 'custom';
  scope_config?: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/** 知识库授权 */
export interface KBAuthorization {
  id: string;
  knowledge_base_id: string;
  knowledge_base_name: string;
  target_type: 'user' | 'role' | 'department' | 'user_group';
  target_id: string;
  target_name: string;
  permission_level: 'read' | 'write' | 'admin';
  granted_by: string;
  granted_at: string;
  expires_at?: string;
}

/** 文档密级 */
export type DocumentClassification = 'public' | 'internal' | 'confidential' | 'secret';

/** 临时授权 */
export interface TemporaryAuthorization {
  id: string;
  user_id: string;
  user_name: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  permission_level: string;
  granted_by: string;
  reason: string;
  starts_at: string;
  expires_at: string;
  is_active: boolean;
  created_at: string;
}

/** 创建临时授权请求 */
export interface TemporaryAuthorizationRequest {
  user_id: string;
  resource_type: string;
  resource_id: string;
  permission_level: string;
  reason: string;
  starts_at: string;
  expires_at: string;
}

/** 权限审计记录 */
export interface PermissionAudit {
  id: string;
  user_id: string;
  user_name: string;
  action: string;
  resource_type: string;
  resource_id: string;
  resource_name: string;
  result: 'allowed' | 'denied';
  deny_reason?: string;
  auth_source: string;
  ip_address: string;
  created_at: string;
}

/** 用户权限摘要 */
export interface UserPermissionSummary {
  user_id: string;
  user_name: string;
  roles: { id: string; name: string }[];
  functional_permissions: string[];
  data_scopes: DataPermissionRule[];
  kb_authorizations: KBAuthorization[];
}

// ==================== 知识库与文档管理相关 ====================

/** 文档处理状态 */
export type DocumentStatus =
  | 'pending'
  | 'uploading'
  | 'uploaded'
  | 'parsing'
  | 'parsed'
  | 'chunking'
  | 'indexing'
  | 'completed'
  | 'failed'
  | 'paused';

/** 文档版本信息 */
export interface DocumentVersion {
  id: string;
  document_id: string;
  version: number;
  file_path: string;
  file_size: number;
  change_summary?: string;
  is_active: boolean;
  created_by: string;
  created_at: string;
}

/** Chunk 信息 */
export interface ChunkInfo {
  id: string;
  document_id: string;
  version: number;
  content: string;
  content_hash: string;
  chunk_index: number;
  char_start: number;
  char_end: number;
  index_status: 'pending' | 'keyword_indexed' | 'vector_indexed' | 'both_indexed' | 'failed';
  metadata?: Record<string, unknown>;
}

/** 索引任务 */
export interface IndexTask {
  id: string;
  document_id: string;
  document_name: string;
  task_type: 'keyword' | 'vector' | 'both';
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  total_chunks: number;
  indexed_chunks: number;
  failed_chunks: number;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  updated_at: string;
}

// ==================== 问答优化相关 ====================

/** 候选问答 */
export interface CandidateQA {
  id: string;
  question: string;
  answer: string;
  source_document_id?: string;
  source_document_name?: string;
  source_chunk_id?: string;
  source_chunk_content?: string;
  source_document_version?: number;
  knowledge_base_id: string;
  knowledge_base_name: string;
  status: 'pending' | 'approved' | 'rejected' | 'revised';
  applicable_roles?: string[];
  applicable_departments?: string[];
  auto_quality_check?: QualityCheckResult;
  review_history: ReviewRecord[];
  created_by: string;
  created_at: string;
  updated_at: string;
}

/** 自动质量检查结果 */
export interface QualityCheckResult {
  score: number;
  issues: { type: string; description: string; severity: 'error' | 'warning' }[];
  checked_at: string;
}

/** 审核记录 */
export interface ReviewRecord {
  reviewer_id: string;
  reviewer_name: string;
  action: 'approve' | 'reject' | 'return_for_revision';
  comment?: string;
  reviewed_at: string;
}

/** 审核动作 */
export type ReviewAction = 'approve' | 'reject' | 'return_for_revision';

/** 问答状态 */
export type QAStatus = 'draft' | 'pending_review' | 'published' | 'unpublished' | 'paused' | 'expired';

/** 相似问句 */
export interface SimilarQuestion {
  id: string;
  question: string;
  standard_qa_id: string;
  created_at: string;
}

/** 高频问题 */
export interface FrequentQuestion {
  question: string;
  count: number;
  last_asked_at: string;
  has_answer: boolean;
}

/** 未命中问题 */
export interface UnmatchedQuestion {
  id: string;
  question: string;
  ask_count: number;
  first_asked_at: string;
  last_asked_at: string;
  status: 'open' | 'reviewing' | 'resolved';
}

/** 低质量答案 */
export interface LowQualityAnswer {
  id: string;
  message_id: string;
  question: string;
  answer: string;
  score: number;
  feedback_count: number;
  negative_ratio: number;
  created_at: string;
}

// ==================== 检索调试相关 ====================

/** 检索调试请求 */
export interface SearchDebugRequest {
  question: string;
  user_id?: string;
  knowledge_base_ids?: string[];
  params?: SearchDebugParams;
}

/** 检索调试参数 */
export interface SearchDebugParams {
  top_k_keyword?: number;
  top_k_vector?: number;
  rrf_k?: number;
  reranker_enabled?: boolean;
  reranker_top_n?: number;
  similarity_threshold?: number;
}

/** 检索调试结果 */
export interface SearchDebugResult {
  request_id: string;
  original_question: string;
  rewritten_question?: string;
  intent?: string;
  keywords: string[];
  entities: string[];
  permission_filter: string;
  matched_qa?: {
    id: string;
    question: string;
    answer: string;
    score: number;
  };
  keyword_results: SearchResultItem[];
  vector_results: SearchResultItem[];
  rrf_results: SearchResultItem[];
  reranker_results: SearchResultItem[];
  final_context: string;
  evidence_coverage: number;
  final_answer?: string;
  references: Reference[];
  rejection_reason?: string;
  stage_timing: StageTiming[];
}

/** 检索结果项 */
export interface SearchResultItem {
  rank: number;
  score: number;
  document_id: string;
  document_name: string;
  chunk_id: string;
  chunk_content: string;
  source: 'keyword' | 'vector' | 'rrf' | 'reranker';
}

/** 引用 */
export interface Reference {
  document_id: string;
  document_name: string;
  chunk_id: string;
  chunk_content: string;
  relevance_score: number;
}

/** 各阶段耗时 */
export interface StageTiming {
  stage: string;
  duration_ms: number;
}

// ==================== 评估中心相关 ====================

/** Golden Dataset */
export interface GoldenDataset {
  id: string;
  name: string;
  description?: string;
  question_count: number;
  created_at: string;
  updated_at: string;
}

/** 评估样本 */
export interface EvaluationSample {
  id: string;
  dataset_id: string;
  question: string;
  expected_answer?: string;
  expected_documents?: string[];
  category?: string;
  difficulty?: 'easy' | 'medium' | 'hard';
}

/** 评估任务 */
export interface EvaluationTask {
  id: string;
  name: string;
  dataset_id: string;
  dataset_name: string;
  task_type: 'single' | 'batch';
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  total_samples: number;
  completed_samples: number;
  failed_samples: number;
  params_config?: Record<string, unknown>;
  results?: EvaluationResult;
  created_at: string;
  completed_at?: string;
}

/** 评估结果 */
export interface EvaluationResult {
  retrieval_metrics: RetrievalMetrics;
  generation_metrics: GenerationMetrics;
  permission_metrics: PermissionMetrics;
  sample_results: SampleResult[];
}

/** 检索指标 */
export interface RetrievalMetrics {
  recall_at_k: Record<number, number>;
  precision_at_k: Record<number, number>;
  mrr: number;
  ndcg: number;
  map: number;
}

/** 生成指标 */
export interface GenerationMetrics {
  bleu: number;
  rouge_l: number;
  faithfulness: number;
  relevance: number;
}

/** 权限指标 */
export interface PermissionMetrics {
  correct_filter_rate: number;
  leak_rate: number;
  over_filter_rate: number;
}

/** 单样本评估结果 */
export interface SampleResult {
  sample_id: string;
  question: string;
  expected_answer: string;
  actual_answer: string;
  retrieved_documents: string[];
  expected_documents: string[];
  metrics: Record<string, number>;
  passed: boolean;
  error_message?: string;
}

// ==================== 安全与审计相关 ====================

/** 查询日志 */
export interface QueryLog {
  id: string;
  user_id: string;
  user_name: string;
  question: string;
  intent?: string;
  matched_qa_id?: string;
  response_time_ms: number;
  result_count: number;
  has_answer: boolean;
  ip_address: string;
  trace_id: string;
  created_at: string;
}

/** 操作日志 */
export interface OperationLog {
  id: string;
  user_id: string;
  user_name: string;
  action: string;
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  detail?: Record<string, unknown>;
  ip_address: string;
  user_agent?: string;
  status_code: number;
  duration_ms: number;
  trace_id: string;
  created_at: string;
}

/** 登录日志 */
export interface LoginLog {
  id: string;
  user_id: string;
  user_name: string;
  login_type: 'password' | 'token' | 'sso';
  ip_address: string;
  user_agent?: string;
  result: 'success' | 'failed';
  fail_reason?: string;
  created_at: string;
}

/** 安全事件类型 */
export type SecurityEventType =
  | 'unauthorized_access'
  | 'prompt_injection'
  | 'brute_force'
  | 'abnormal_login'
  | 'data_leak'
  | 'permission_escalation';

/** 安全事件级别 */
export type SecurityEventSeverity = 'low' | 'medium' | 'high' | 'critical';

/** 安全事件 */
export interface SecurityEvent {
  id: string;
  event_type: SecurityEventType;
  severity: SecurityEventSeverity;
  user_id?: string;
  user_name?: string;
  ip_address: string;
  description: string;
  detail?: Record<string, unknown>;
  resolved: boolean;
  resolved_at?: string;
  resolved_by?: string;
  created_at: string;
}

// ==================== 系统设置相关 ====================

/** 配置项 */
export interface SystemConfig {
  id: string;
  config_key: string;
  config_value: string;
  value_type: 'string' | 'number' | 'boolean' | 'json';
  description?: string;
  is_sensitive: boolean;
  is_configured: boolean;
  updated_at: string;
  updated_by: string;
}

/** LLM 配置 */
export interface LLMConfig {
  provider: string;
  model: string;
  api_base: string;
  api_key_configured: boolean;
  max_tokens: number;
  temperature: number;
  timeout: number;
}

/** Embedding 配置 */
export interface EmbeddingConfig {
  provider: string;
  model: string;
  api_base: string;
  api_key_configured: boolean;
  dimension: number;
  batch_size: number;
}

/** Reranker 配置 */
export interface RerankerConfig {
  provider: string;
  model: string;
  api_base: string;
  api_key_configured: boolean;
  top_n: number;
}

/** 检索参数配置 */
export interface RetrievalConfig {
  top_k_keyword: number;
  top_k_vector: number;
  rrf_k: number;
  similarity_threshold: number;
  reranker_enabled: boolean;
  reranker_top_n: number;
}

/** 提示词模板 */
export interface PromptTemplate {
  id: string;
  name: string;
  template_type: string;
  content: string;
  variables: string[];
  is_default: boolean;
  updated_at: string;
}

/** 系统健康状态 */
export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  components: {
    postgresql: ComponentHealth;
    redis: ComponentHealth;
    opensearch: ComponentHealth;
    minio: ComponentHealth;
    celery: ComponentHealth;
  };
  uptime_hours: number;
  memory_usage_percent: number;
  cpu_usage_percent: number;
  disk_usage_percent: number;
}

/** 组件健康状态 */
export interface ComponentHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms: number;
  message?: string;
}

// ==================== 通用管理后台类型 ====================

/** 分页查询参数 */
export interface AdminPaginationParams {
  page: number;
  page_size: number;
}

/** 排序参数 */
export interface AdminSortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/** 筛选参数 */
export interface AdminFilterParams {
  keyword?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

/** 管理后台菜单项 */
export interface AdminMenuItem {
  key: string;
  label: string;
  icon?: string;
  path: string;
  children?: AdminMenuItem[];
  /** 所需权限编码 */
  permission_code?: string;
}

/** 操作确认配置 */
export interface ConfirmActionConfig {
  title: string;
  content: string | React.ReactNode;
  danger?: boolean;
  okText?: string;
  cancelText?: string;
  onOk: () => Promise<void> | void;
  /** 影响说明 */
  impactDescription?: string;
}