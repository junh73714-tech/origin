/**
 * 管理后台公共组件 - 数据表格
 * 成员3：管理后台前端
 * 统一的数据表格组件，封装分页、排序、筛选、空状态
 */
import { Table, type TableProps, type TablePaginationConfig } from 'antd';
import type { SorterResult, FilterValue } from 'antd/es/table/interface';
import { EmptyState } from '@/components/shared';

export interface DataTableProps<T extends Record<string, unknown>>
  extends Omit<TableProps<T>, 'onChange' | 'pagination'> {
  /** 当前页码 */
  page?: number;
  /** 每页条数 */
  pageSize?: number;
  /** 总条数 */
  total?: number;
  /** 是否加载中 */
  loading?: boolean;
  /** 分页/排序/筛选变更回调 */
  onChange?: (
    page: number,
    pageSize: number,
    sorter?: SorterResult<T>,
    filters?: Record<string, FilterValue | null>
  ) => void;
  /** 空状态描述 */
  emptyDescription?: string;
  /** 空状态操作文字 */
  emptyActionText?: string;
  /** 空状态操作回调 */
  onEmptyAction?: () => void;
}

/**
 * 数据表格组件
 * 统一管理后台表格样式、分页、空状态
 */
export function DataTable<T extends Record<string, unknown>>({
  page = 1,
  pageSize = 20,
  total = 0,
  loading = false,
  onChange,
  emptyDescription = '暂无数据',
  emptyActionText,
  onEmptyAction,
  rowKey = 'id',
  size = 'middle',
  bordered = false,
  ...restProps
}: DataTableProps<T>) {
  /** 分页配置 */
  const pagination: TablePaginationConfig | false = total > 0 ? {
    current: page,
    pageSize: pageSize,
    total: total,
    showSizeChanger: true,
    showQuickJumper: true,
    pageSizeOptions: ['10', '20', '50', '100'],
    showTotal: (total: number, range: [number, number]) =>
      `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
  } : false;

  /** 表格变更处理 */
  const handleTableChange: TableProps<T>['onChange'] = (
    pagination,
    filters,
    sorter
  ) => {
    const newPage = (pagination as TablePaginationConfig).current || 1;
    const newPageSize = (pagination as TablePaginationConfig).pageSize || 20;
    onChange?.(
      newPage,
      newPageSize,
      sorter as SorterResult<T>,
      filters as Record<string, FilterValue | null>
    );
  };

  return (
    <Table<T>
      rowKey={rowKey}
      size={size}
      bordered={bordered}
      loading={loading}
      pagination={pagination}
      onChange={handleTableChange}
      locale={{
        emptyText: (
          <EmptyState
            title="暂无数据"
            description={emptyDescription}
            actionText={emptyActionText}
            onAction={onEmptyAction}
          />
        ),
      }}
      scroll={{ x: 'max-content' }}
      {...restProps}
    />
  );
}