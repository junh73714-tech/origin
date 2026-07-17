import { Typography, Card } from 'antd';
import { HistoryOutlined } from '@ant-design/icons';
const { Title, Text } = Typography;
export function Component() {
  return <Card><Title level={3}><HistoryOutlined /> 历史记录</Title><Text type="secondary">历史对话记录（成员2实现）</Text></Card>;
}