import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RefusalNotice } from '@/components/user/chat/RefusalNotice';
import { renderMarkdown } from '@/utils/markdown';

describe('拒答展示与 Markdown 安全渲染', () => {
  it('拒答提示展示原因', () => {
    render(<RefusalNotice reason="证据不足，无法作答。" />);
    expect(screen.getByText('证据不足，无法作答。')).toBeInTheDocument();
  });

  it('Markdown 渲染剔除 script（防 XSS）', () => {
    const html = renderMarkdown('正常文本<script>alert(1)</script>');
    expect(html).not.toContain('<script>');
    expect(html).toContain('正常文本');
  });

  it('外部链接补充安全属性', () => {
    const html = renderMarkdown('[链接](https://example.com)');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain('target="_blank"');
  });
});
