// 反馈与推荐问题 API（成员7契约）。
import { http, unwrap } from './http';
import { USE_MOCK } from './env';
import { feedbackMock } from '@/mocks/feedbackMock';
import type { ApiResponse } from '@/types/common';
import type { FeedbackRequest, RecommendedQuestion } from '@/types/chat';

export const feedbackApi = {
  async submit(payload: FeedbackRequest): Promise<void> {
    if (USE_MOCK) return feedbackMock.submit(payload);
    await http.post('/feedback', payload);
  },

  async recommendedQuestions(): Promise<RecommendedQuestion[]> {
    if (USE_MOCK) return feedbackMock.recommendedQuestions();
    const { data } =
      await http.get<ApiResponse<RecommendedQuestion[]>>('/questions/recommended');
    return unwrap(data);
  },
};
