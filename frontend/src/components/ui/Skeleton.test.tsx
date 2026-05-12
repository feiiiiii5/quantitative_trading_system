import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { Skeleton, SkeletonCard, SkeletonTable } from './Skeleton';

describe('Skeleton', () => {
  it('renders with default props', () => {
    const { container } = render(<Skeleton />);
    const el = container.firstChild as HTMLElement;
    expect(el).toBeInTheDocument();
    expect(el.style.width).toBe('100%');
    expect(el.style.height).toBe('1rem');
  });

  it('renders with custom width and height', () => {
    const { container } = render(<Skeleton width="200px" height="2rem" />);
    const el = container.firstChild as HTMLElement;
    expect(el.style.width).toBe('200px');
    expect(el.style.height).toBe('2rem');
  });
});

describe('SkeletonCard', () => {
  it('renders default 3 rows', () => {
    const { container } = render(<SkeletonCard />);
    const skeletons = container.querySelectorAll('[style*="animation"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(4);
  });

  it('renders custom row count', () => {
    const { container } = render(<SkeletonCard rows={5} />);
    const skeletons = container.querySelectorAll('[style*="animation"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(6);
  });
});

describe('SkeletonTable', () => {
  it('renders default 4 columns and 5 rows', () => {
    const { container } = render(<SkeletonTable />);
    const skeletons = container.querySelectorAll('[style*="animation"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(24);
  });

  it('renders custom dimensions', () => {
    const { container } = render(<SkeletonTable columns={2} rows={2} />);
    const skeletons = container.querySelectorAll('[style*="animation"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(6);
  });
});
