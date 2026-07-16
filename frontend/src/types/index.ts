/**
 * 类型定义
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  request_id?: string;
}

export interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
  request_id?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface FilterParams {
  keyword?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

// 菜单项
export interface MenuItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  path?: string;
  children?: MenuItem[];
}

// 表格列配置
export interface TableColumn<T = any> {
  title: string;
  dataIndex: keyof T | string[];
  key: string;
  width?: number | string;
  fixed?: 'left' | 'right';
  align?: 'left' | 'center' | 'right';
  render?: (value: any, record: T, index: number) => React.ReactNode;
  filters?: { text: string; value: string }[];
  onFilter?: (value: string, record: T) => boolean;
  sorter?: boolean | ((a: T, b: T) => number);
}

// 表单配置
export interface FormField {
  name: string;
  label: string;
  type: 'input' | 'textarea' | 'select' | 'date' | 'datetime' | 'number' | 'switch' | 'upload';
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  rules?: any[];
  options?: { label: string; value: any }[];
  props?: Record<string, any>;
}
