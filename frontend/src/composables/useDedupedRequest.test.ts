import { describe, it, expect, vi, beforeEach } from 'vitest'
import { dedupedRequest, clearDedupCache, getPendingCount } from './useDedupedRequest'

describe('useDedupedRequest', () => {
  beforeEach(() => {
    clearDedupCache()
  })

  it('deduplicates concurrent requests to same key', async () => {
    let callCount = 0
    const fetcher = () => {
      callCount++
      return new Promise<string>(resolve => setTimeout(() => resolve('result'), 10))
    }

    const [r1, r2, r3] = await Promise.all([
      dedupedRequest('key-a', fetcher),
      dedupedRequest('key-a', fetcher),
      dedupedRequest('key-a', fetcher),
    ])

    expect(r1).toBe('result')
    expect(r2).toBe('result')
    expect(r3).toBe('result')
    expect(callCount).toBe(1)
  })

  it('allows different keys to execute independently', async () => {
    let callCount = 0
    const fetcher = () => {
      callCount++
      return Promise.resolve('result')
    }

    await Promise.all([
      dedupedRequest('key-x', fetcher),
      dedupedRequest('key-y', fetcher),
    ])

    expect(callCount).toBe(2)
  })

  it('removes pending entry after TTL', async () => {
    vi.useFakeTimers()

    const fetcher = () => Promise.resolve('done')
    await dedupedRequest('ttl-key', fetcher)

    expect(getPendingCount()).toBe(1)

    vi.advanceTimersByTime(5_000)
    expect(getPendingCount()).toBe(0)

    vi.useRealTimers()
  })

  it('removes pending entry even when fetcher rejects', async () => {
    vi.useFakeTimers()

    const fetcher = () => Promise.reject(new Error('fail'))

    await expect(dedupedRequest('err-key', fetcher)).rejects.toThrow('fail')
    expect(getPendingCount()).toBe(1)

    vi.advanceTimersByTime(5_000)
    expect(getPendingCount()).toBe(0)

    vi.useRealTimers()
  })

  it('clearDedupCache removes all pending entries', async () => {
    const slowFetcher = () => new Promise(r => setTimeout(r, 10_000))
    dedupedRequest('c1', slowFetcher)
    dedupedRequest('c2', slowFetcher)

    expect(getPendingCount()).toBe(2)
    clearDedupCache()
    expect(getPendingCount()).toBe(0)
  })
})
