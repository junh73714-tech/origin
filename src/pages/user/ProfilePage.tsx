import { useEffect } from 'react';
import { Card, Descriptions, Tag, Space, Typography, Badge } from 'antd';
import { useAuthStore } from '@/stores/authStore';
import { usePermissionStore } from '@/stores/permissionStore';
import { formatDateTime } from '@/utils/format';
import { LoadingState } from '@/components/user/common/LoadingState';

const STATUS_BADGE: Record<string, { status: 'success' | 'error' | 'warning'; text: string }> = {
  active: { status: 'success', text: '正常' },
  disabled: { status: 'error', text: '已禁用' },
  locked: { status: 'warning', text: '已锁定' },
};

/** 个人信息与权限摘要页：仅展示后端计算结果，不做权限推导 */
export function ProfilePage() {
  const user = useAuthStore((s) => s.user);
  const summary = usePermissionStore((s) => s.summary);
  const loading = usePermissionStore((s) => s.loading);
  const load = usePermissionStore((s) => s.load);

  useEffect(() => {
    if (!summary) load();
  }, [summary, load]);

  if (!user) return <LoadingState tip="加载用户信息" />;

  const badge = STATUS_BADGE[user.account_status] ?? STATUS_BADGE.active;

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      <Card title="基本信息">
        <Descriptions column={2}>
          <Descriptions.Item label="用户名">{user.username}</Descriptions.Item>
          <Descriptions.Item label="姓名">{user.display_name}</Descriptions.Item>
          <Descriptions.Item label="部门">{user.department.name}</Descriptions.Item>
          <Descriptions.Item label="用户组">
            {user.user_groups.length
              ? user.user_groups.map((g) => g.name).join('、')
              : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="角色">
            {user.roles.length ? user.roles.join('、') : '—'}
          </Descriptions.Item>
          <Descriptions.Item label="账号状态">
            <Badge status={badge.status} text={badge.text} />
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="可访问知识库" loading={loading}>
        {summary && summary.knowledge_scopes.length > 0 ? (
          <Space size={[8, 8]} wrap>
            {summary.knowledge_scopes.map((k) => (
              <Tag key={k.knowledge_base_id} color="blue">
                {k.name}（{k.access_level}）
              </Tag>
            ))}
          </Space>
        ) : (
          <Typography.Text type="secondary">暂无可访问的知识库</Typography.Text>
        )}
      </Card>

      {summary && summary.data_scopes.length > 0 ? (
        <Card title="数据范围">
          <Space size={[8, 8]} wrap>
            {summary.data_scopes.map((s) => (
              <Tag key={s.scope_id} color="geekblue">
                {s.description ?? s.scope_type}
              </Tag>
            ))}
          </Space>
        </Card>
      ) : null}

      <Card title="临时授权" loading={loading}>
        {summary && summary.temporary_grants.length > 0 ? (
          <Descriptions column={1} size="small">
            {summary.temporary_grants.map((g) => (
              <Descriptions.Item key={g.grant_id} label={g.resource_name}>
                到期时间：{formatDateTime(g.expires_at)}
              </Descriptions.Item>
            ))}
          </Descriptions>
        ) : (
          <Typography.Text type="secondary">暂无临时授权</Typography.Text>
        )}
      </Card>
    </Space>
  );
}
