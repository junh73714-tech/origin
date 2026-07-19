// Markdown 安全渲染：marked 转 HTML 后经 DOMPurify 净化，防止 XSS。
// 外部链接强制加 rel="noopener noreferrer" 与 target="_blank"。
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({ breaks: true, gfm: true });

// 为所有链接补充安全属性
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

/** 将 Markdown 文本渲染为安全 HTML 字符串 */
export function renderMarkdown(text: string): string {
  const rawHtml = marked.parse(text ?? '', { async: false }) as string;
  return DOMPurify.sanitize(rawHtml, {
    ALLOWED_TAGS: [
      'p', 'br', 'strong', 'em', 'del', 'blockquote',
      'ul', 'ol', 'li', 'code', 'pre', 'a', 'h1', 'h2', 'h3', 'h4',
      'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr', 'span',
    ],
    ALLOWED_ATTR: ['href', 'title', 'target', 'rel', 'class'],
  });
}
