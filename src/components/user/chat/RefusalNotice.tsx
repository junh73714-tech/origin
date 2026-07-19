import { Alert } from 'antd';

interface RefusalNoticeProps {
  reason?: string;
}

/** 拒答提示：证据不足、无权限或证据冲突时展示明确原因 */
export function RefusalNotice({ reason }: RefusalNoticeProps) {
  return (
    <Alert
      type="warning"
      showIcon
      message="暂无法给出确定答案"
      description={reason || '现有证据不足以生成可靠答案。'}
    />
  );
}
