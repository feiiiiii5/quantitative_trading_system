import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePolling } from './usePolling'

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  it('calls fn immediately when immediate is true', () => {
    const fn = vi.fn()
    usePolling(fn, { immediate: true, interval: 10_000 })
    expect(fn).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('does not call fn immediately when immediate is false', () => {
    const fn = vi.fn()
    usePolling(fn, { immediate: false, interval: 10_000 })
    expect(fn).not.toHaveBeenCalled()
    vi.useRealTimers()
  })

  it('calls fn at the specified interval using recursive setTimeout', async () => {
    const fn = vi.fn()
    usePolling(fn, { immediate: false, interval: 5_000 })
    expect(fn).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(5_000)
    expect(fn).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(5_000)
    expect(fn).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })

  it('does not overlap when fn takes longer than interval', async () => {
    let resolveFn: () => void
    const fn = vi.fn(() => new Promise<void>((r) => { resolveFn = r }))
    usePolling(fn, { immediate: false, interval: 1_000 })

    await vi.advanceTimersByTimeAsync(1_000)
    expect(fn).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(5_000)
    expect(fn).toHaveBeenCalledTimes(1)

    resolveFn!()
    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(1_000)
    expect(fn).toHaveBeenCalledTimes(2)

    vi.useRealTimers()
  })

  it('stop halts the polling', async () => {
    const fn = vi.fn()
    const { stop } = usePolling(fn, { immediate: false, interval: 5_000 })
    await vi.advanceTimersByTimeAsync(5_000)
    expect(fn).toHaveBeenCalledTimes(1)
    stop()
    await vi.advanceTimersByTimeAsync(15_000)
    expect(fn).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('execute calls fn directly', async () => {
    const fn = vi.fn()
    const { execute } = usePolling(fn, { immediate: false, interval: 60_000 })
    await execute()
    expect(fn).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })

  it('isActive reflects polling state', () => {
    const fn = vi.fn()
    const { isActive, stop, start } = usePolling(fn, { immediate: false, interval: 10_000 })
    expect(isActive.value).toBe(true)
    stop()
    expect(isActive.value).toBe(false)
    start()
    expect(isActive.value).toBe(true)
    vi.useRealTimers()
  })
})
