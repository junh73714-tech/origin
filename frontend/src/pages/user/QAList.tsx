import { Typography, Card } from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
const { Title, Text } = Typography;
export function Component() {
  return <Card><Title level={3}><QuestionCircleOutlined /> 标准问答</Title><Text type="secondary">标准问答列表（成员2实现）</Text></Card>;
}