/**
 * 公共组件 - 加载状态
 */
import { Spin, Typography } from 'antd';

const { Text } = Typography;

interface LoadingStateProps {
  tip?: string;
  size?: 'small' | 'default' | 'large';
  fullScreen?: boolean;
}

export function LoadingState({ tip = '加载中...', size = 'default', fullScreen = false }: LoadingStateProps) {
  if (fullScreen) {
    return (
      <div
        style={{
          width: '100vw',
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Spin size={size} tip={tip} />
      </div>
    );
  }

  return (
    <Spin size={size} tip={tip}>
      {/* Ant Design Spin 的 tip 仅在嵌套模式或全屏模式下生效，需要包裹一个容器 */}
      <div style={{ minHeight: 200 }} />
    </Spin>
  );
}
