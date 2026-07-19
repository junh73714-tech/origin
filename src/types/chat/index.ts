// 会话与消息、引用、SSE 事件类型。位于成员2主责目录 types/chat/。
// 依赖成员6接口契约（会话、SSE、引用）与成员7接口（反馈、推荐问题）。

/** 答案类型：标准问答 / RAG 生成 / 参考答案 / 拒答 */
export type AnswerType = 'standard_qa' | 'rag' | 'reference' | 'refusal';

/** 证据/可信度状态 */
export type EvidenceStatus = 'sufficient' | 'insufficient' | 'conflict' | 'none';

/** 消息角色 */
export type MessageRole = 'user' | 'assistant';

/** 消息发送/接收状态 */
export type MessageStatus =
  | 'pending' // 已提交，等待首个事件
  | 'streaming' // 流式接收中
  | 'done' // 完成（以 done 事件为准）
  | 'stopped' // 用户停止生成
  | 'error'; // 失败，可重试

/** 引用角标（随流式 citation 事件到达，仅含可公开展示字段） */
export interface Citation {
  citation_id: string; // 仅凭此 id 取详情，前端不拼接存储地址
  index: number; // 引用编号
  document_name: string;
  snippet?: string; // 简短引用预览
}

/** 引用详情（点击后按 citation_id 拉取，无权限时后端返回受限标记） */
export interface CitationDetail {
  citation_id: string;
  document_name: string;
  title_path: string[]; // 标题路径
  page_no?: number;
  quoted_text: string; // 引用原文
  document_version: string;
  effective_time: string; // 生效时间 ISO8601
  source_type: string; // 来源类型
  can_open_source: boolean; // 是否有权打开原文
  source_url?: string; // 仅在有权限时后端下发，前端不自行拼接
  access_denied?: boolean; // 无权限标记
}

/** 单条消息 */
export interface ChatMessage {
  message_id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  answer_type?: AnswerType;
  evidence_status?: EvidenceStatus;
  citations?: Citation[];
  refusal_reason?: string; // 拒答原因
  error_message?: string; // 失败提示（面向用户，非堆栈）
  created_at: string;
}

/** 会话摘要（历史列表用） */
export interface Conversation {
  conversation_id: string;
  title: string;
  updated_at: string;
  archived: boolean;
  message_count: number;
}

/** 会话详情 */
export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

/** 发送问题请求（成员6契约修订）：
 *  路径 /qa/chat；body 字段 content（不是 question），conversation_id 可为 null。
 */
export interface AskRequest {
  conversation_id?: string | null; // null 或缺省表示新建会话
  content: string;
}

/* -------------------- SSE 流式事件（成员6契约修订） -------------------- */

/** 后端会下发的事件类型集合（与实测对齐） */
export type SseEventType =
  | 'message_start' // { conversation_id, message_id, trace_id, answer_type, query_id }
  | 'message' // { content, done, references[] }   ← 完整消息（可能一次性下发）
  | 'answer_delta' // { content, done }            ← 增量片段
  | 'citation' // { citation } 或可选未使用
  | 'metadata' // { refusal_reason, query_id, timings_ms, ... }
  | 'error' // { code, message }
  | 'done'; // POST 流中可能 data 为空；GET 流中含 { answer, citations, ... }

export interface SseMessageStart {
  conversation_id: string;
  message_id: string;
  trace_id?: string;
  answer_type?: AnswerType;
  query_id?: string;
}

/** message 事件：可能是一次性下发的完整内容（拒答/短答案） */
export interface SseMessage {
  content: string;
  done: boolean;
  references?: Citation[];
}

/** answer_delta 增量事件载荷 */
export interface SseAnswerDelta {
  content: string; // 增量文本片段
  done?: boolean;
}

/** citation 事件载荷（若后端单发） */
export interface SseCitation {
  citation: Citation;
}

/** metadata 事件载荷：含 refusal_reason / query_id / timings 等 */
export interface SseMetadata {
  answer_type?: AnswerType;
  refusal_reason?: string;
  query_id?: string;
  cache_hit?: boolean;
  request_id?: string;
  timings_ms?: Record<string, number>;
  cancelled?: boolean;
  [k: string]: unknown;
}

export interface SseError {
  code: string;
  message: string;
}

/** done 事件载荷：POST 流中可能为空，GET 流中含完整 answer/citations */
export interface SseDone {
  message_id?: string;
  conversation_id?: string;
  answer?: string;
  answer_type?: AnswerType;
  evidence_status?: EvidenceStatus;
  citations?: Citation[];
  refusal_reason?: string | null;
  query_id?: string;
  trace_id?: string;
  [k: string]: unknown;
}

/** 统一的 SSE 事件联合类型 */
export type SseEvent =
  | { event: 'message_start'; data: SseMessageStart }
  | { event: 'message'; data: SseMessage }
  | { event: 'answer_delta'; data: SseAnswerDelta }
  | { event: 'citation'; data: SseCitation }
  | { event: 'metadata'; data: SseMetadata }
  | { event: 'error'; data: SseError }
  | { event: 'done'; data?: SseDone };

/* -------------------- 反馈与推荐（成员7契约） -------------------- */

export type FeedbackType = 'like' | 'dislike' | 'correction';

export interface FeedbackRequest {
  message_id: string;
  conversation_id: string;
  feedback_type: FeedbackType;
  correction_text?: string; // 纠错内容
}

export interface RecommendedQuestion {
  id: string;
  text: string;
  category?: string;
}
