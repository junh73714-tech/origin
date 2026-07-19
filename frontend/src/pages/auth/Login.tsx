import { Typography, Card } from 'antd';
import { LoginOutlined } from '@ant-design/icons';
const { Title, Text } = Typography;
export function Component() {
  return <Card><Title level={3}><LoginOutlined /> 登录</Title><Text type="secondary">用户登录页面（成员2实现）</Text></Card>;
}