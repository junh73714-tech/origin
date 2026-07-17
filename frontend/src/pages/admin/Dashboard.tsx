/**
 * 管理后台 - 工作台页面
 * 成员3：管理后台前端 - 4.1 工作台
 * 展示知识库、文档、问答、系统等核心指标卡片
 */
import { useEffect } from 'react';
import { Row, Col, Typography, Select, Spin } from 'antd';
import {
  DatabaseOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SearchOutlined,
  QuestionCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { MetricCard } from '@/components/admin';
import { useAdminStore } from '@/stores/admin';
import type { TimeRange } from '@/types/admin';
import styles from '@/layouts/admin/AdminLayout.module.css';

const { Title, Text } = Typography;

/**
 * 工作台页面
 * 以卡片网格展示系统核心指标
 */
export function Dashboard() {
  const {
    dashboardStats,
    dashboardTimeRange,
    setDashboardTimeRange,
    dashboardLoading,
    setDashboardLoading,
  } = useAdminStore();

  // 模拟数据加载（实际开发中替换为真实 API 调用）
  useEffect(() => {
    setDashboardLoading(true);
    const timer = setTimeout(() => {
      setDashboardLoading(false);
    }, 500);
    return () => clearTimeout(timer);
  }, [dashboardTimeRange, setDashboardLoading]);

  // 异常指标样式（红色高亮）
  const warningStyle: React.CSSProperties = { color: '#ff4d4f' };

  // 时间范围选项
  const timeRangeOptions: { label: string; value: TimeRange }[] = [
    { label: '今日', value: 'today' },
    { label: '本周', value: 'week' },
    { label: '本月', value: 'month' },
    { label: '本季度', value: 'quarter' },
    { label: '本年', value: 'year' },
  ];

  return (
    <div>
      {/* 页面标题 */}
      <div className={styles.pageHeader}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} className={styles.pageTitle}>
              工作台
            </Title>
            <Text type="secondary" className={styles.pageSubtitle}>
              系统运行概览与核心指标监控
            </Text>
          </div>
          {/* 时间范围选择 */}
          <Select
            value={dashboardTimeRange}
            onChange={(value) => setDashboardTimeRange(value)}
            options={timeRangeOptions}
            style={{ width: 120 }}
          />
        </div>
      </div>

      {/* 指标卡片网格 - 3列布局 */}
      <Spin spinning={dashboardLoading}>
        <div className={styles.cardGrid}>
          {/* 知识库数量 */}
          <MetricCard
            title="知识库数量"
            value={dashboardStats?.kb_count ?? 0}
            unit="个"
            icon={<DatabaseOutlined />}
            iconBgColor="#e6f4ff"
            iconColor="#1677ff"
            loading={dashboardLoading}
          />

          {/* 文档总数 */}
          <MetricCard
            title="文档总数"
            value={dashboardStats?.document_count ?? 0}
            unit="份"
            icon={<FileTextOutlined />}
            iconBgColor="#f0f5ff"
            iconColor="#597ef7"
            loading={dashboardLoading}
          />

          {/* 已发布文档 */}
          <MetricCard
            title="已发布文档"
            value={dashboardStats?.published_document_count ?? 0}
            unit="份"
            icon={<CheckCircleOutlined />}
            iconBgColor="#f6ffed"
            iconColor="#52c41a"
            loading={dashboardLoading}
          />

          {/* 文档处理失败 */}
          <MetricCard
            title="处理失败"
            value={dashboardStats?.failed_document_count ?? 0}
            unit="份"
            icon={<CloseCircleOutlined />}
            iconBgColor="#fff2f0"
            iconColor="#ff4d4f"
            loading={dashboardLoading}
            valueStyle={
              (dashboardStats?.failed_document_count ?? 0) > 0 ? warningStyle : undefined
            }
            subtitle={
              dashboardStats && dashboardStats.failed_document_count > 0
                ? '需处理'
                : undefined
            }
          />

          {/* 今日查询量 */}
          <MetricCard
            title="今日查询量"
            value={dashboardStats?.today_query_count ?? 0}
            unit="次"
            icon={<SearchOutlined />}
            iconBgColor="#fff7e6"
            iconColor="#fa8c16"
            loading={dashboardLoading}
          />

          {/* 标准问答命中率 */}
          <MetricCard
            title="问答命中率"
            value={
              dashboardStats
                ? `${(dashboardStats.qa_hit_rate * 100).toFixed(1)}%`
                : '0%'
            }
            icon={<CheckCircleOutlined />}
            iconBgColor="#f6ffed"
            iconColor="#52c41a"
            loading={dashboardLoading}
          />

          {/* 拒答率 */}
          <MetricCard
            title="拒答率"
            value={
              dashboardStats
                ? `${(dashboardStats.rejection_rate * 100).toFixed(1)}%`
                : '0%'
            }
            icon={<QuestionCircleOutlined />}
            iconBgColor="#e6f4ff"
            iconColor="#1677ff"
            loading={dashboardLoading}
          />

          {/* 未命中问题 */}
          <MetricCard
            title="未命中问题"
            value={dashboardStats?.unmatched_question_count ?? 0}
            unit="个"
            icon={<ExclamationCircleOutlined />}
            iconBgColor="#fff7e6"
            iconColor="#fa8c16"
            loading={dashboardLoading}
            valueStyle={
              (dashboardStats?.unmatched_question_count ?? 0) > 0
                ? warningStyle
                : undefined
            }
          />

          {/* 低质量答案 */}
          <MetricCard
            title="低质量答案"
            value={dashboardStats?.low_quality_answer_count ?? 0}
            unit="个"
            icon={<WarningOutlined />}
            iconBgColor="#fff2f0"
            iconColor="#ff4d4f"
            loading={dashboardLoading}
            valueStyle={
              (dashboardStats?.low_quality_answer_count ?? 0) > 0
                ? warningStyle
                : undefined
            }
          />

          {/* 平均响应时间 */}
          <MetricCard
            title="平均响应时间"
            value={dashboardStats?.avg_response_time_ms ?? 0}
            unit="ms"
            icon={<ClockCircleOutlined />}
            iconBgColor="#f0f5ff"
            iconColor="#597ef7"
            loading={dashboardLoading}
          />

          {/* 风险事件 */}
          <MetricCard
            title="风险事件"
            value={dashboardStats?.risk_event_count ?? 0}
            unit="起"
            icon={<WarningOutlined />}
            iconBgColor="#fff2f0"
            iconColor="#ff4d4f"
            loading={dashboardLoading}
            valueStyle={
              (dashboardStats?.risk_event_count ?? 0) > 0 ? warningStyle : undefined
            }
            subtitle={
              dashboardStats && dashboardStats.risk_event_count > 0
                ? '需立即处理'
                : undefined
            }
          />
        </div>
      </Spin>

      {/* 快捷操作区 */}
      <div style={{ marginTop: 24 }}>
        <Title level={5} style={{ marginBottom: 12 }}>
          快捷操作
        </Title>
        <Row gutter={16}>
          <Col span={6}>
            <div
              className={styles.contentCard}
              style={{ textAlign: 'center', cursor: 'pointer' }}
            >
              <FileTextOutlined
                style={{ fontSize: 24, color: '#1677ff', marginBottom: 8 }}
              />
              <div>
                <Text strong>上传文档</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  添加新知识文档
                </Text>
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div
              className={styles.contentCard}
              style={{ textAlign: 'center', cursor: 'pointer' }}
            >
              <DatabaseOutlined
                style={{ fontSize: 24, color: '#597ef7', marginBottom: 8 }}
              />
              <div>
                <Text strong>创建知识库</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  建立新的知识空间
                </Text>
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div
              className={styles.contentCard}
              style={{ textAlign: 'center', cursor: 'pointer' }}
            >
              <QuestionCircleOutlined
                style={{ fontSize: 24, color: '#52c41a', marginBottom: 8 }}
              />
              <div>
                <Text strong>审核问答</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  查看待审核的问题
                </Text>
              </div>
            </div>
          </Col>
          <Col span={6}>
            <div
              className={styles.contentCard}
              style={{ textAlign: 'center', cursor: 'pointer' }}
            >
              <SearchOutlined
                style={{ fontSize: 24, color: '#fa8c16', marginBottom: 8 }}
              />
              <div>
                <Text strong>检索调试</Text>
              </div>
              <div>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  测试检索效果
                </Text>
              </div>
            </div>
          </Col>
        </Row>
      </div>
    </div>
  );
}