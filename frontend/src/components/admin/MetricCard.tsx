/**
 * 管理后台公共组件 - 指标卡片
 * 成员3：管理后台前端
 * 用于工作台的数据概览卡片，左侧彩色图标 + 右侧文字信息
 */
import { Card, Statistic, Typography, type CardProps } from 'antd';
import styles from './MetricCard.module.css';

const { Text } = Typography;

export interface MetricCardProps {
  /** 指标标题 */
  title: string;
  /** 指标数值 */
  value: number | string;
  /** 数值单位 */
  unit?: string;
  /** 副标题（如较昨日变化） */
  subtitle?: string;
  /** 左侧图标 */
  icon?: React.ReactNode;
  /** 图标背景色 */
  iconBgColor?: string;
  /** 图标颜色 */
  iconColor?: string;
  /** 点击跳转回调 */
  onClick?: () => void;
  /** 是否加载中 */
  loading?: boolean;
  /** 数值前缀 */
  prefix?: React.ReactNode;
  /** 数值样式（用于异常数值高亮） */
  valueStyle?: React.CSSProperties;
  /** 额外 Card 属性 */
  cardProps?: CardProps;
}

/**
 * 指标卡片组件
 * 左侧彩色方形图标 + 右侧标题数值，符合企业后台风格
 */
export function MetricCard({
  title,
  value,
  unit,
  subtitle,
  icon,
  iconBgColor = '#e6f4ff',
  iconColor = '#1677ff',
  onClick,
  loading = false,
  prefix,
  valueStyle,
  cardProps,
}: MetricCardProps) {
  return (
    <Card
      hoverable={!!onClick}
      onClick={onClick}
      loading={loading}
      className={styles.metricCard}
      bodyStyle={{ padding: '20px' }}
      {...cardProps}
    >
      <div className={styles.metricContent}>
        {/* 左侧彩色图标 */}
        {icon && (
          <div
            className={styles.metricIcon}
            style={{ backgroundColor: iconBgColor, color: iconColor }}
          >
            {icon}
          </div>
        )}

        {/* 右侧文字信息 */}
        <div className={styles.metricInfo}>
          <Text type="secondary" className={styles.metricTitle}>
            {title}
          </Text>
          <div className={styles.metricValue}>
            <Statistic
              value={value}
              prefix={prefix}
              suffix={unit ? <Text type="secondary" className={styles.metricUnit}>{unit}</Text> : undefined}
              valueStyle={{
                fontSize: '28px',
                fontWeight: 700,
                color: '#1f1f1f',
                ...valueStyle,
              }}
              loading={loading}
            />
          </div>
          {subtitle && (
            <Text type="secondary" className={styles.metricSubtitle}>
              {subtitle}
            </Text>
          )}
        </div>
      </div>
    </Card>
  );
}