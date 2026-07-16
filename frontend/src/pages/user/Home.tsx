/**
 * 用户端首页（占位页面）
 * 成员2：用户问答前端 主责
 */
import { Typography, Card } from 'antd';
import { HomeOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

export function Component() {
  return (
    <Card>
      <Title level={3}><HomeOutlined /> 首页</Title>
      <Text type="secondary">欢迎使用 RAG 知识问答平台</Text>
    </Card>
  );
}