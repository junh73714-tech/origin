/**
 * 公共组件 - 错误状态
 */
import { Result, Button, Typography } from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';

const { Paragraph } = Typography;

interface ErrorStateProps {
  title?: string;
  description?: string;
  error?: Error | any;
  onRetry?: () => void;
}

export function ErrorState({
  title = '出错了',
  description,
  error,
  onRetry,
}: ErrorStateProps) {
  return (
    <Result
      status="error"
      title={title}
      subTitle={description || error?.message || '请稍后重试'}
      extra={[
        onRetry && (
          <Button key="retry" type="primary" icon={<ReloadOutlined />} onClick={onRetry}>
            重试
          </Button>
        ),
        <Button key="home" icon={<HomeOutlined />} onClick={() => window.location.href = '/'}>
          返回首页
        </Button>,
      ]}
    >
      {error && (
        <Paragraph>
          <pre
            style={{
              background: '#f5f5f5',
              padding: 16,
              borderRadius: 4,
              overflow: 'auto',
              maxHeight: 200,
            }}
          >
            {JSON.stringify(error, null, 2)}
          </pre>
        </Paragraph>
      )}
    </Result>
  );
}
