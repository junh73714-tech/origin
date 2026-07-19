import { renderMarkdown } from '@/utils/markdown';

interface StreamingAnswerProps {
  content: string;
  streaming: boolean;
}

/** 流式答案文本：Markdown 安全渲染，生成中显示光标 */
export function StreamingAnswer({ content, streaming }: StreamingAnswerProps) {
  return (
    <div className="assistant-markdown">
      <span
        // 内容已由 DOMPurify 净化，防止 XSS
        dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
      />
      {streaming ? <span className="typing-cursor">▍</span> : null}
    </div>
  );
}
