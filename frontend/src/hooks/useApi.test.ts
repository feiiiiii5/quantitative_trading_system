import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useApiGet, useApiPost } from './useApi';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('@/api/client', () => ({
  apiGet: (...args: unknown[]) => mockGet(...args),
  apiPost: (...args: unknown[]) => mockPost(...args),
}));

describe('useApiGet', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('starts with loading=true when immediate=true', async () => {
    mockGet.mockResolvedValue({ foo: 'bar' });
    const { result } = renderHook(() => useApiGet('/test', {}, { immediate: true }));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it('starts with loading=false when immediate=false', () => {
    const { result } = renderHook(() => useApiGet('/test', {}, { immediate: false }));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it('sets data on success', async () => {
    mockGet.mockResolvedValue({ foo: 'bar' });
    const { result } = renderHook(() => useApiGet('/test', {}, { immediate: true }));
    await waitFor(() => expect(result.current.data).toEqual({ foo: 'bar' }));
    expect(result.current.error).toBeNull();
  });

  it('sets error on failure', async () => {
    mockGet.mockRejectedValue(new Error('Network error'));
    const { result } = renderHook(() => useApiGet('/test', {}, { immediate: true }));
    await waitFor(() => expect(result.current.error).toBe('Network error'));
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('refetch triggers new request', async () => {
    mockGet.mockResolvedValue({ count: 1 });
    const { result } = renderHook(() => useApiGet('/test', {}, { immediate: false }));
    result.current.refetch();
    await waitFor(() => expect(result.current.data).toEqual({ count: 1 }));
    expect(mockGet).toHaveBeenCalledTimes(1);
  });
});

describe('useApiPost', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts with loading=false', () => {
    const { result } = renderHook(() => useApiPost('/test', { name: 'foo' }));
    expect(result.current.loading).toBe(false);
  });

  it('sets data on success', async () => {
    mockPost.mockResolvedValue({ id: 1 });
    const { result } = renderHook(() => useApiPost('/test', { name: 'foo' }));
    result.current.execute();
    await waitFor(() => expect(result.current.data).toEqual({ id: 1 }));
    expect(result.current.error).toBeNull();
  });

  it('allows override body', async () => {
    mockPost.mockResolvedValue({ id: 2 });
    const { result } = renderHook(() => useApiPost('/test', { name: 'foo' }));
    result.current.execute({ name: 'bar' });
    await waitFor(() => expect(result.current.data).toEqual({ id: 2 }));
    expect(mockPost).toHaveBeenCalledWith('/test', { name: 'bar' }, undefined);
  });
});
