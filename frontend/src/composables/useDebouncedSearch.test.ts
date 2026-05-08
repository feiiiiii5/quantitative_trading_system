import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import { useDebouncedSearch } from './useDebouncedSearch'

describe('useDebouncedSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('does not call searchFn immediately', async () => {
    const searchFn = vi.fn().mockResolvedValue(undefined)
    const { query } = useDebouncedSearch(searchFn, 300)
    query.value = 'test'
    await nextTick()
    expect(searchFn).not.toHaveBeenCalled()
  })

  it('calls searchFn after delay', async () => {
    const searchFn = vi.fn().mockResolvedValue(undefined)
    const { query } = useDebouncedSearch(searchFn, 300)
    query.value = 'test'
    await nextTick()
    vi.advanceTimersByTime(300)
    await nextTick()
    expect(searchFn).toHaveBeenCalledWith('test')
  })

  it('debounces rapid changes', async () => {
    const searchFn = vi.fn().mockResolvedValue(undefined)
    const { query } = useDebouncedSearch(searchFn, 300)
    query.value = 'a'
    await nextTick()
    vi.advanceTimersByTime(100)
    query.value = 'ab'
    await nextTick()
    vi.advanceTimersByTime(100)
    query.value = 'abc'
    await nextTick()
    vi.advanceTimersByTime(300)
    await nextTick()
    expect(searchFn).toHaveBeenCalledTimes(1)
    expect(searchFn).toHaveBeenCalledWith('abc')
  })

  it('does not search empty query', async () => {
    const searchFn = vi.fn().mockResolvedValue(undefined)
    const { query } = useDebouncedSearch(searchFn, 300)
    query.value = '   '
    await nextTick()
    vi.advanceTimersByTime(300)
    expect(searchFn).not.toHaveBeenCalled()
  })

  it('sets loading to true while debouncing', async () => {
    const searchFn = vi.fn().mockResolvedValue(undefined)
    const { query, loading } = useDebouncedSearch(searchFn, 300)
    query.value = 'test'
    await nextTick()
    expect(loading.value).toBe(true)
  })

  it('sets loading to false after search completes', async () => {
    const searchFn = vi.fn().mockResolvedValue(undefined)
    const { query, loading } = useDebouncedSearch(searchFn, 300)
    query.value = 'test'
    await nextTick()
    vi.advanceTimersByTime(300)
    await vi.runAllTimersAsync()
    expect(loading.value).toBe(false)
  })

  it('sets loading to false for empty query', async () => {
    const searchFn = vi.fn().mockResolvedValue(undefined)
    const { query, loading } = useDebouncedSearch(searchFn, 300)
    query.value = 'test'
    await nextTick()
    expect(loading.value).toBe(true)
    query.value = '   '
    await nextTick()
    expect(loading.value).toBe(false)
  })
})
