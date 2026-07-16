/**
 * 管理后台公共组件 - 权限门控
 * 成员3：管理后台前端
 * 根据功能权限编码控制子组件的渲染
 * 前端权限仅改善体验，不替代后端校验
 */
import { Result, Button } from 'antd';
import { LockOutlined } from '@ant-design/icons';

export interface PermissionGateProps {
  /** 所需权限编码 */
  permissionCode: string;
  /** 用户拥有的权限列表 */
  userPermissions: string[];
  /** 子组件 */
  children: React.ReactNode;
  /** 无权限时显示的内容，不传则显示默认无权限页面 */
  fallback?: React.ReactNode;
  /** 是否显示无权限提示页面（而非不渲染） */
  showDenied?: boolean;
}

/**
 * 权限门控组件
 * 根据用户权限编码控制内容渲染
 * - 有权限：正常渲染子组件
 * - 无权限且 showDenied=true：显示无权限提示
 * - 无权限且 showDenied=false：不渲染任何内容
 */
export function PermissionGate({
  permissionCode,
  userPermissions,
  children,
  fallback,
  showDenied = false,
}: PermissionGateProps) {
  // 检查是否拥有所需权限
  const hasPermission = userPermissions.includes(permissionCode);

  if (hasPermission) {
    return <>{children}</>;
  }

  // 无权限时的处理
  if (showDenied) {
    return (
      fallback || (
        <Result
          icon={<LockOutlined />}
          title="权限不足"
          subTitle="您没有访问此功能的权限，请联系管理员"
          extra={
            <Button type="primary" onClick={() => window.history.back()}>
              返回上一页
            </Button>
          }
        />
      )
    );
  }

  // 默认不渲染
  return null;
}