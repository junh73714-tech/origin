import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { EmptyState } from '@/components/shared/EmptyState';

describe('EmptyState', () => {
  it('renders with default title', () => {
    render(<EmptyState />);
    expect(screen.getByText('暂无数据')).toBeInTheDocument();
  });

  it('renders with custom title', () => {
    render(<EmptyState title="没有文档" />);
    expect(screen.getByText('没有文档')).toBeInTheDocument();
  });

  it('renders with description', () => {
    render(<EmptyState description="请先上传文档" />);
    expect(screen.getByText('请先上传文档')).toBeInTheDocument();
  });

  it('renders action button when provided', () => {
    const onAction = () => {};
    render(<EmptyState actionText="上传文档" onAction={onAction} />);
    expect(screen.getByText('上传文档')).toBeInTheDocument();
  });
});
