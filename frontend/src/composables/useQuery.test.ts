import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import { useQuery, invalidateQuery, setQueryData, clearQueryCache, getCacheSize } from './useQuery'

describe('useQuery', () => {
  beforeEach(() => {
    clearQueryCache()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('fetches data on creation', async () => {
    const fetcher = vi.fn().mockResolvedValue({ name: 'test' })
    const { data, isLoading, isFetching } = useQuery({
      key: 'test-1',
      fetcher,
    })

    expect(isLoading.value).toBe(true)
    expect(isFetching.value).toBe(true)

    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(data.value).toEqual({ name: 'test' })
    expect(isLoading.value).toBe(false)
    expect(isFetching.value).toBe(false)
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('stores error on fetch failure', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('fetch failed'))
    const { data, error } = useQuery({
      key: 'test-error',
      fetcher,
    })

    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(data.value).toBeNull()
    expect(error.value).toBeInstanceOf(Error)
    expect(error.value?.message).toBe('fetch failed')
  })

  it('uses cached data for same key', async () => {
    const fetcher = vi.fn().mockResolvedValue('first')
    const q1 = useQuery({ key: 'cache-test', fetcher })
    await vi.runAllTimersAsync()
    await Promise.resolve()

    const fetcher2 = vi.fn().mockResolvedValue('second')
    const q2 = useQuery({ key: 'cache-test', fetcher: fetcher2, staleTime: 60_000 })
    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(q2.data.value).toBe('first')
    expect(fetcher2).not.toHaveBeenCalled()
  })

  it('refetches when data is stale', async () => {
    const fetcher = vi.fn().mockResolvedValue('fresh')
    const { data } = useQuery({
      key: 'stale-test',
      fetcher,
      staleTime: 5_000,
    })

    await vi.runAllTimersAsync()
    await Promise.resolve()
    expect(data.value).toBe('fresh')

    vi.advanceTimersByTime(6_000)

    const fetcher2 = vi.fn().mockResolvedValue('newer')
    const q2 = useQuery({
      key: 'stale-test',
      fetcher: fetcher2,
      staleTime: 5_000,
    })
    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(q2.data.value).toBe('newer')
    expect(fetcher2).toHaveBeenCalledTimes(1)
  })

  it('does not fetch when enabled is false', async () => {
    const fetcher = vi.fn().mockResolvedValue('data')
    const { data, isLoading } = useQuery({
      key: 'disabled-test',
      fetcher,
      enabled: false,
    })

    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(fetcher).not.toHaveBeenCalled()
    expect(data.value).toBeNull()
    expect(isLoading.value).toBe(false)
  })

  it('fetches when enabled becomes true', async () => {
    const fetcher = vi.fn().mockResolvedValue('enabled-data')
    const enabledRef = ref(false)
    const { data } = useQuery({
      key: 'enable-test',
      fetcher,
      enabled: enabledRef,
    })

    await vi.runAllTimersAsync()
    await Promise.resolve()
    expect(fetcher).not.toHaveBeenCalled()

    enabledRef.value = true
    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(data.value).toBe('enabled-data')
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('refetch manually via refetch()', async () => {
    let callCount = 0
    const fetcher = vi.fn().mockImplementation(() => {
      callCount++
      return Promise.resolve(`call-${callCount}`)
    })

    const { data, refetch } = useQuery({
      key: 'refetch-test',
      fetcher,
      staleTime: 0,
    })

    await vi.runAllTimersAsync()
    await Promise.resolve()
    expect(data.value).toBe('call-1')

    vi.advanceTimersByTime(1)
    await refetch()
    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(fetcher).toHaveBeenCalledTimes(2)
  })

  it('deduplicates concurrent fetches for same key', async () => {
    let resolveFirst: (v: string) => void
    const fetcher = vi.fn().mockImplementation(
      () => new Promise<string>((resolve) => { resolveFirst = resolve })
    )

    const q1 = useQuery({ key: 'dedup-test', fetcher })
    const q2 = useQuery({ key: 'dedup-test', fetcher })

    resolveFirst!('deduped')
    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(q1.data.value).toBe('deduped')
    expect(q2.data.value).toBe('deduped')
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('isStale is true before fetch and false after', async () => {
    const fetcher = vi.fn().mockResolvedValue('stale-check')
    const { isStale } = useQuery({
      key: 'stale-value-test',
      fetcher,
      staleTime: 10_000,
    })

    expect(isStale.value).toBe(true)

    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(isStale.value).toBe(false)
  })
})

describe('invalidateQuery', () => {
  beforeEach(() => {
    clearQueryCache()
  })

  it('invalidates entries matching prefix', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn().mockResolvedValue('data')
    useQuery({ key: 'market/overview', fetcher, staleTime: 60_000 })
    useQuery({ key: 'market/status', fetcher, staleTime: 60_000 })
    useQuery({ key: 'strategy/list', fetcher, staleTime: 60_000 })

    await vi.runAllTimersAsync()
    await Promise.resolve()

    invalidateQuery('market')
    expect(getCacheSize()).toBe(3)
    clearQueryCache()
    vi.useRealTimers()
  })
})

describe('setQueryData', () => {
  beforeEach(() => {
    clearQueryCache()
  })

  it('sets data directly into cache', () => {
    setQueryData('manual-key', { value: 42 })
    const fetcher = vi.fn().mockResolvedValue('should-not-call')
    const { data } = useQuery({
      key: 'manual-key',
      fetcher,
      staleTime: 60_000,
    })

    expect(data.value).toEqual({ value: 42 })
    expect(fetcher).not.toHaveBeenCalled()
    clearQueryCache()
  })
})

describe('clearQueryCache', () => {
  beforeEach(() => {
    clearQueryCache()
  })

  it('clears all entries', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn().mockResolvedValue('x')
    useQuery({ key: 'clear-a', fetcher })
    useQuery({ key: 'clear-b', fetcher })

    await vi.runAllTimersAsync()
    await Promise.resolve()

    expect(getCacheSize()).toBe(2)
    clearQueryCache()
    expect(getCacheSize()).toBe(0)
    vi.useRealTimers()
  })
})
