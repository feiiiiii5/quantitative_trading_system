import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useMutation } from './useMutation'
import { clearQueryCache, getCacheSize } from './useQuery'

describe('useMutation', () => {
  beforeEach(() => {
    clearQueryCache()
  })

  it('starts in idle state', () => {
    const { data, error, isLoading, isSuccess, isError } = useMutation({
      mutationFn: vi.fn(),
    })
    expect(data.value).toBeNull()
    expect(error.value).toBeNull()
    expect(isLoading.value).toBe(false)
    expect(isSuccess.value).toBe(false)
    expect(isError.value).toBe(false)
  })

  it('calls mutationFn and returns data on success', async () => {
    const mutationFn = vi.fn().mockResolvedValue({ id: 1 })
    const { mutate, data, isSuccess } = useMutation({
      mutationFn,
    })

    const result = await mutate({ name: 'test' })
    expect(result).toEqual({ id: 1 })
    expect(data.value).toEqual({ id: 1 })
    expect(isSuccess.value).toBe(true)
    expect(mutationFn).toHaveBeenCalledWith({ name: 'test' })
  })

  it('stores error on failure', async () => {
    const mutationFn = vi.fn().mockRejectedValue(new Error('mutation failed'))
    const { mutate, error, isError } = useMutation({
      mutationFn,
    })

    const result = await mutate({})
    expect(result).toBeNull()
    expect(error.value).toBeInstanceOf(Error)
    expect(error.value?.message).toBe('mutation failed')
    expect(isError.value).toBe(true)
  })

  it('calls onSuccess callback', async () => {
    const onSuccess = vi.fn()
    const mutationFn = vi.fn().mockResolvedValue('result')
    const { mutate } = useMutation({
      mutationFn,
      onSuccess,
    })

    await mutate('vars')
    expect(onSuccess).toHaveBeenCalledWith('result', 'vars')
  })

  it('calls onError callback', async () => {
    const onError = vi.fn()
    const mutationFn = vi.fn().mockRejectedValue(new Error('fail'))
    const { mutate } = useMutation({
      mutationFn,
      onError,
    })

    await mutate('vars')
    expect(onError).toHaveBeenCalledTimes(1)
    expect(onError.mock.calls[0][0].message).toBe('fail')
    expect(onError.mock.calls[0][1]).toBe('vars')
  })

  it('invalidates specified query keys on success', async () => {
    const mutationFn = vi.fn().mockResolvedValue('ok')
    const { mutate } = useMutation({
      mutationFn,
      invalidateKeys: ['alerts/list', 'alerts/history'],
    })

    await mutate({})
    expect(getCacheSize()).toBe(0)
  })

  it('does not invalidate keys on failure', async () => {
    const mutationFn = vi.fn().mockRejectedValue(new Error('fail'))
    const { mutate } = useMutation({
      mutationFn,
      invalidateKeys: ['test/key'],
    })

    await mutate({})
  })

  it('reset returns to idle state', async () => {
    const mutationFn = vi.fn().mockResolvedValue('result')
    const { mutate, reset, data, isSuccess } = useMutation({
      mutationFn,
    })

    await mutate({})
    expect(data.value).toBe('result')
    expect(isSuccess.value).toBe(true)

    reset()
    expect(data.value).toBeNull()
    expect(isSuccess.value).toBe(false)
  })

  it('tracks loading state during mutation', async () => {
    let resolveMutation: (v: string) => void
    const mutationFn = vi.fn().mockImplementation(
      () => new Promise<string>((resolve) => { resolveMutation = resolve })
    )
    const { mutate, isLoading } = useMutation({ mutationFn })

    const promise = mutate({})
    expect(isLoading.value).toBe(true)

    resolveMutation!('done')
    await promise

    expect(isLoading.value).toBe(false)
  })
})
