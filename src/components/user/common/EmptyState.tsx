import { Empty } from 'antd';
import type { ReactNode } from 'react';

interface EmptyStateProps {
  description: string;
  extra?: ReactNode;
}

/** 通用空状态 */
export function EmptyState({ description, extra }: EmptyStateProps) {
  return (
    <div style={{ padding: '48px 0', textAlign: 'center' }}>
      <Empty description={description} />
      {extra ? <div style={{ marginTop: 16 }}>{extra}</div> : null}
    </div>
  );
}
