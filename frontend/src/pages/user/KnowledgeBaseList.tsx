import { Typography, Card } from 'antd';
import { DatabaseOutlined } from '@ant-design/icons';
const { Title, Text } = Typography;
export function Component() {
  return <Card><Title level={3}><DatabaseOutlined /> 知识库</Title><Text type="secondary">知识库列表（成员2实现）</Text></Card>;
}