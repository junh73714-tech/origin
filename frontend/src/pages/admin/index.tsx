/**
 * 管理后台页面导出
 * 成员3：管理后台前端
 */
export { Dashboard } from './Dashboard';

// ========== M2: 用户与组织（已实现） ==========
export { UserManagement } from './UserManagement';
export { DepartmentManagement } from './DepartmentManagement';
export { RoleManagement } from './RoleManagement';

// ========== M2: 知识库与文档（已实现） ==========
export { AdminKBList } from './AdminKBList';
export { AdminDocList } from './AdminDocList';
export { IndexTaskManagement } from './IndexTaskManagement';

// 以下 M2 页面和 M3/M4 页面为占位，将在后续里程碑中逐步实现
import { Typography } from 'antd';
import { ToolOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

/** 占位页面工厂函数 */
function createPlaceholderPage(title: string, description: string) {
  return function PlaceholderPage() {
    return (
      <div style={{ textAlign: 'center', padding: '80px 20px' }}>
        <ToolOutlined style={{ fontSize: 48, color: '#1677ff', marginBottom: 16 }} />
        <Title level={3}>{title}</Title>
        <Text type="secondary">{description}</Text>
        <br />
        <Text type="secondary" style={{ fontSize: 12 }}>
          （此页面将在后续里程碑中实现）
        </Text>
      </div>
    );
  };
}

// ========== M2 剩余：用户与组织 ==========
export const UserGroupManage = createPlaceholderPage('用户组管理', '用户组创建与成员管理');
export const TempAuthManage = createPlaceholderPage('临时授权', '临时权限授予与有效期管理');

// ========== M2 剩余：权限中心 ==========
export const PermissionManage = createPlaceholderPage('功能权限', '功能权限定义与分配');
export const DataPermissionManage = createPlaceholderPage('数据权限', '数据范围权限规则');
export const KBAuthManage = createPlaceholderPage('知识库授权', '知识库访问权限管理');
export const DocClassification = createPlaceholderPage('文档密级', '文档密级分类管理');
export const PermissionRules = createPlaceholderPage('权限规则', 'ABAC 权限规则配置');
export const PermissionAudit = createPlaceholderPage('权限审计', '权限使用审计记录');

// ========== M2 剩余：知识库与文档 ==========
export const DocVersionManage = createPlaceholderPage('文档版本', '文档版本历史与切换');
export const ChunkView = createPlaceholderPage('Chunk 查看', '文档分块内容查看');

// ========== 问答优化 ==========
export const CandidateQA = createPlaceholderPage('候选问答', '自动生成的候选问答列表');
export const PendingReview = createPlaceholderPage('待审核问答', '问答审核（通过/驳回/返回修改）');
export const StandardQA = createPlaceholderPage('标准问答', '已发布的标准问答管理');
export const SimilarQuestions = createPlaceholderPage('相似问句', '相似问句管理');
export const FrequentQuestions = createPlaceholderPage('高频问题', '高频问题统计');
export const UnmatchedQuestions = createPlaceholderPage('未命中问题', '未命中问题处理');
export const LowQualityAnswers = createPlaceholderPage('低质量答案', '低质量答案分析与改进');

// ========== 检索调试 ==========
export const SearchDebug = createPlaceholderPage('检索调试', '检索过程调试与结果分析');

// ========== 评估中心 ==========
export const EvalDatasets = createPlaceholderPage('Golden Dataset', '评估数据集管理');
export const EvalSamples = createPlaceholderPage('评估样本', '评估样本管理');
export const EvalTasks = createPlaceholderPage('评估任务', '评估任务创建与进度查看');
export const EvalHistory = createPlaceholderPage('历史评估', '历史评估结果查看');
export const EvalCompare = createPlaceholderPage('参数对比', '检索参数配置对比');

// ========== 安全与审计 ==========
export const QueryLogs = createPlaceholderPage('查询日志', '用户查询记录与追踪');
export const OperationLogs = createPlaceholderPage('操作日志', '管理员操作审计记录');
export const LoginLogs = createPlaceholderPage('登录日志', '用户登录记录');
export const SecurityEvents = createPlaceholderPage('安全事件', '越权、注入等安全事件');
export const RiskAlerts = createPlaceholderPage('风险告警', '安全风险告警列表');

// ========== 系统设置 ==========
export const LLMConfig = createPlaceholderPage('LLM 配置', '大语言模型配置');
export const EmbeddingConfig = createPlaceholderPage('Embedding 配置', '向量嵌入模型配置');
export const RerankerConfig = createPlaceholderPage('Reranker 配置', '重排序模型配置');
export const OCRConfig = createPlaceholderPage('OCR 配置', '文档识别配置');
export const RetrievalConfig = createPlaceholderPage('检索参数', '检索运行参数配置');
export const PromptTemplates = createPlaceholderPage('提示词模板', '提示词模板管理');
export const SystemHealth = createPlaceholderPage('系统健康', '系统组件健康状态监控');