import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { useUiStore } from '@/stores/uiStore';
import { CitationDrawer } from '@/components/user/citation/CitationDrawer';

// 验证引用抽屉：正常引用展示原文与打开按钮；无权限引用不泄露地址与正文
describe('CitationDrawer 引用抽屉与权限', () => {
  beforeEach(() => {
    useUiStore.getState().reset();
  });

  it('有权限引用：展示原文与打开原文按钮', async () => {
    render(<CitationDrawer />);
    useUiStore.getState().openCitation('cite-001');
    await waitFor(() => {
      expect(screen.getByText('产品使用手册')).toBeInTheDocument();
    });
    expect(screen.getByText('打开原文')).toBeInTheDocument();
  });

  it('无权限引用：显示无权提示，不展示真实地址与正文', async () => {
    render(<CitationDrawer />);
    useUiStore.getState().openCitation('cite-restricted');
    await waitFor(() => {
      expect(screen.getByText('无权查看该引用')).toBeInTheDocument();
    });
    expect(screen.queryByText('打开原文')).not.toBeInTheDocument();
  });
});
