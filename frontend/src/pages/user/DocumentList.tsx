import { Typography, Card } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
const { Title, Text } = Typography;
export function Component() {
  return <Card><Title level={3}><FileTextOutlined /> 文档列表</Title><Text type="secondary">知识库文档列表（成员2实现）</Text></Card>;
}