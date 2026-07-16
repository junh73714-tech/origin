/**
 * 管理后台公共组件 - 筛选栏
 * 成员3：管理后台前端
 * 统一的搜索和筛选组件，包含关键词搜索、状态筛选、日期范围筛选
 */
import { Input, Select, DatePicker, Button, Space } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;

export interface FilterItem {
  /** 筛选字段名 */
  key: string;
  /** 显示标签 */
  label: string;
  /** 筛选类型 */
  type: 'keyword' | 'select' | 'dateRange' | 'date';
  /** 占位文字 */
  placeholder?: string;
  /** 下拉选项（type 为 select 时必填） */
  options?: { label: string; value: string }[];
  /** 是否允许清空 */
  allowClear?: boolean;
  /** 宽度 */
  width?: number | string;
}

export interface FilterBarProps {
  /** 筛选项配置 */
  filters: FilterItem[];
  /** 筛选值 */
  values: Record<string, unknown>;
  /** 值变更回调 */
  onChange: (key: string, value: unknown) => void;
  /** 搜索回调 */
  onSearch: () => void;
  /** 重置回调 */
  onReset: () => void;
  /** 是否显示搜索按钮 */
  showSearchButton?: boolean;
  /** 是否显示重置按钮 */
  showResetButton?: boolean;
  /** 是否加载中 */
  loading?: boolean;
  /** 额外操作按钮 */
  extra?: React.ReactNode;
}

/**
 * 筛选栏组件
 * 统一的表格筛选栏，支持关键词、下拉选择、日期范围
 */
export function FilterBar({
  filters,
  values,
  onChange,
  onSearch,
  onReset,
  showSearchButton = true,
  showResetButton = true,
  loading = false,
  extra,
}: FilterBarProps) {
  /** 渲染单个筛选控件 */
  const renderFilter = (filter: FilterItem) => {
    const { key, type, placeholder, options, allowClear = true, width } = filter;

    switch (type) {
      case 'keyword':
        return (
          <Input
            key={key}
            placeholder={placeholder || '请输入关键词搜索'}
            prefix={<SearchOutlined />}
            allowClear={allowClear}
            value={(values[key] as string) || ''}
            onChange={(e) => onChange(key, e.target.value)}
            onPressEnter={onSearch}
            style={{ width: width || 200 }}
          />
        );

      case 'select':
        return (
          <Select
            key={key}
            placeholder={placeholder || '请选择'}
            allowClear={allowClear}
            value={(values[key] as string) || undefined}
            onChange={(value) => onChange(key, value)}
            options={options}
            style={{ width: width || 150 }}
          />
        );

      case 'dateRange':
        return (
          <RangePicker
            key={key}
            value={(values[key] as [Dayjs, Dayjs]) || undefined}
            onChange={(dates) => onChange(key, dates)}
            allowClear={allowClear}
            style={{ width: width || 260 }}
          />
        );

      case 'date':
        return (
          <DatePicker
            key={key}
            value={(values[key] as Dayjs) || undefined}
            onChange={(date) => onChange(key, date)}
            allowClear={allowClear}
            style={{ width: width || 160 }}
          />
        );

      default:
        return null;
    }
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <Space wrap size="middle" style={{ width: '100%' }}>
        {/* 筛选控件 */}
        {filters.map(renderFilter)}

        {/* 操作按钮 */}
        {showSearchButton && (
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={onSearch}
            loading={loading}
          >
            搜索
          </Button>
        )}
        {showResetButton && (
          <Button icon={<ReloadOutlined />} onClick={onReset}>
            重置
          </Button>
        )}

        {/* 额外操作 */}
        {extra && <div style={{ marginLeft: 'auto' }}>{extra}</div>}
      </Space>
    </div>
  );
}