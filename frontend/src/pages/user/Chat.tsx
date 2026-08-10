import { Typography, Card } from 'antd';
import { MessageOutlined } from '@ant-design/icons';
const { Title, Text } = Typography;
export function Component() {
  return <Card><Title level={3}><MessageOutlined /> 智能问答</Title><Text type="secondary">问答页面（成员2实现）</Text></Card>;
}