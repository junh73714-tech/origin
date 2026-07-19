// 反馈与推荐问题 Mock（对齐成员7契约）。
import type { FeedbackRequest, RecommendedQuestion } from '@/types/chat';

function delay<T>(value: T, ms = 200): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

export const feedbackMock = {
  async submit(_payload: FeedbackRequest): Promise<void> {
    return delay(undefined as void);
  },

  async recommendedQuestions(): Promise<RecommendedQuestion[]> {
    return delay([
      { id: 'q-1', text: '如何重置账号密码？', category: '账号' },
      { id: 'q-2', text: '产品导出功能如何使用？', category: '功能' },
      { id: 'q-3', text: '数据备份策略是什么？', category: '运维' },
      { id: 'q-4', text: '如何申请知识库访问权限？', category: '权限' },
    ]);
  },
};
