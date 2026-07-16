import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { LoadingState } from '@/components/shared/LoadingState';

describe('LoadingState', () => {
  it('renders with default tip', () => {
    render(<LoadingState />);
    expect(screen.getByText('加载中...')).toBeInTheDocument();
  });

  it('renders with custom tip', () => {
    render(<LoadingState tip="正在加载数据..." />);
    expect(screen.getByText('正在加载数据...')).toBeInTheDocument();
  });
});
