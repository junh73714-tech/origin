/**
 * 管理后台公共组件 - JSON 查看器
 * 成员3：管理后台前端
 * 格式化展示 JSON 数据，支持折叠/展开
 */
import { Typography, Button, Space } from 'antd';
import { CopyOutlined, ExpandOutlined, CompressOutlined } from '@ant-design/icons';
import { useState } from 'react';

const { Text } = Typography;

export interface JsonViewerProps {
  /** JSON 数据 */
  data: unknown;
  /** 最大高度（超出滚动） */
  maxHeight?: number;
  /** 是否默认展开所有层级 */
  defaultExpanded?: boolean;
  /** 是否显示复制按钮 */
  showCopy?: boolean;
}

/**
 * JSON 查看器组件
 * 格式化展示 JSON 数据，支持复制和展开/折叠
 * 用于检索调试结果、配置项等场景
 */
export function JsonViewer({
  data,
  maxHeight = 400,
  defaultExpanded = true,
  showCopy = true,
}: JsonViewerProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  /** 格式化 JSON */
  const formattedJson = JSON.stringify(data, null, 2);

  /** 复制到剪贴板 */
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(formattedJson);
    } catch {
      // 降级方案：使用 textarea
      const textarea = document.createElement('textarea');
      textarea.value = formattedJson;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
  };

  /** 折叠/展开 */
  const toggleExpand = () => {
    setExpanded(!expanded);
  };

  return (
    <div
      style={{
        border: '1px solid #f0f0f0',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      {/* 工具栏 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          background: '#fafafa',
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <Text type="secondary" style={{ fontSize: 12 }}>
          JSON
        </Text>
        <Space size="small">
          {showCopy && (
            <Button
              size="small"
              type="text"
              icon={<CopyOutlined />}
              onClick={handleCopy}
            >
              复制
            </Button>
          )}
          <Button
            size="small"
            type="text"
            icon={expanded ? <CompressOutlined /> : <ExpandOutlined />}
            onClick={toggleExpand}
          >
            {expanded ? '折叠' : '展开'}
          </Button>
        </Space>
      </div>

      {/* JSON 内容 */}
      <div
        style={{
          maxHeight: expanded ? maxHeight : 0,
          overflow: 'auto',
          transition: 'max-height 0.3s ease',
          padding: expanded ? '12px' : 0,
        }}
      >
        <pre
          style={{
            margin: 0,
            fontFamily: "'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace",
            fontSize: 13,
            lineHeight: 1.6,
            color: '#1f1f1f',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}
        >
          {formattedJson}
        </pre>
      </div>
    </div>
  );
}