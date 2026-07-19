import { Button, Result } from 'antd';

interface ErrorStateProps {
  title?: string;
  description: string;
  onRetry?: () => void;
}

/** 通用错误状态，仅展示可理解提示，不暴露后端堆栈 */
export function ErrorState({ title = '服务异常', description, onRetry }: ErrorStateProps) {
  return (
    <Result
      status="warning"
      title={title}
      subTitle={description}
      extra={
        onRetry ? (
          <Button type="primary" onClick={onRetry}>
            重试
          </Button>
        ) : null
      }
    />
  );
}
