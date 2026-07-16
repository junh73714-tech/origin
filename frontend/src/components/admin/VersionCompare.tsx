/**
 * 管理后台公共组件 - 版本对比
 * 成员3：管理后台前端
 * 对比两个版本的差异，用于文档版本、问答版本等场景
 */
import { Typography, Empty, Tag, Space, Divider } from 'antd';
import { SwapOutlined } from '@ant-design/icons';

const { Text, Paragraph } = Typography;

/** 版本对比字段 */
export interface VersionCompareField {
  /** 字段名 */
  label: string;
  /** 旧值 */
  oldValue: string | number | null;
  /** 新值 */
  newValue: string | number | null;
  /** 是否变更 */
  changed: boolean;
}

export interface VersionCompareProps {
  /** 旧版本标签 */
  oldVersionLabel: string;
  /** 新版本标签 */
  newVersionLabel: string;
  /** 对比字段列表 */
  fields: VersionCompareField[];
  /** 是否显示未变更的字段 */
  showUnchanged?: boolean;
}

/**
 * 版本对比组件
 * 左右对比展示两个版本的字段差异
 * 变更的字段高亮显示
 */
export function VersionCompare({
  oldVersionLabel,
  newVersionLabel,
  fields,
  showUnchanged = false,
}: VersionCompareProps) {
  // 过滤未变更字段（若不需要显示）
  const displayFields = showUnchanged
    ? fields
    : fields.filter((f) => f.changed);

  if (displayFields.length === 0) {
    return (
      <Empty description="两个版本无差异" />
    );
  }

  return (
    <div>
      {/* 版本标签 */}
      <Space style={{ marginBottom: 16 }}>
        <Tag color="blue">{oldVersionLabel}</Tag>
        <SwapOutlined />
        <Tag color="green">{newVersionLabel}</Tag>
      </Space>

      <Divider style={{ margin: '12px 0' }} />

      {/* 字段对比列表 */}
      <div style={{ maxHeight: 500, overflow: 'auto' }}>
        {displayFields.map((field, index) => (
          <div
            key={index}
            style={{
              padding: '12px 8px',
              borderBottom: '1px solid #f0f0f0',
              background: field.changed ? '#fffbe6' : 'transparent',
              borderRadius: 4,
              marginBottom: 4,
            }}
          >
            {/* 字段名 */}
            <Text
              type="secondary"
              style={{ fontSize: 12, display: 'block', marginBottom: 4 }}
            >
              {field.label}
              {field.changed && (
                <Tag color="orange" style={{ marginLeft: 8, fontSize: 10 }}>
                  已变更
                </Tag>
              )}
            </Text>

            {/* 旧值和新值 */}
            <div style={{ display: 'flex', gap: 16, marginTop: 4 }}>
              {/* 旧值 */}
              <div style={{ flex: 1 }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  旧值：
                </Text>
                <Paragraph
                  delete={field.changed}
                  style={{
                    margin: 0,
                    padding: '4px 8px',
                    background: '#fff1f0',
                    borderRadius: 4,
                    fontSize: 13,
                  }}
                >
                  {field.oldValue != null ? String(field.oldValue) : (
                    <Text type="secondary">（空）</Text>
                  )}
                </Paragraph>
              </div>

              {/* 新值 */}
              <div style={{ flex: 1 }}>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  新值：
                </Text>
                <Paragraph
                  style={{
                    margin: 0,
                    padding: '4px 8px',
                    background: field.changed ? '#f6ffed' : '#fafafa',
                    borderRadius: 4,
                    fontSize: 13,
                  }}
                >
                  {field.newValue != null ? String(field.newValue) : (
                    <Text type="secondary">（空）</Text>
                  )}
                </Paragraph>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}