import { Spin } from 'antd';

interface LoadingStateProps {
  tip?: string;
}

/** 通用加载状态 */
export function LoadingState({ tip = '加载中' }: LoadingStateProps) {
  return (
    <div style={{ padding: '48px 0', textAlign: 'center' }}>
      <Spin tip={tip}>
        <div style={{ minHeight: 40 }} />
      </Spin>
    </div>
  );
}
