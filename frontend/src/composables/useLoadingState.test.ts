import { describe, it, expect, vi } from 'vitest'
import { useLoadingState } from './useLoadingState'

vi.mock('./useToast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

describe('useLoadingState', () => {
  it('initializes with null data, not loading, empty error', () => {
    const { data, loading, error } = useLoadingState<string>()
    expect(data.value).toBeNull()
    expect(loading.value).toBe(false)
    expect(error.value).toBe('')
  })

  it('wrap sets loading during execution and data on success', async () => {
    const { data, loading, error, wrap } = useLoadingState<string>()
    const promise = wrap(() => Promise.resolve('ok'))
    expect(loading.value).toBe(true)
    const result = await promise
    expect(result).toBe('ok')
    expect(data.value).toBe('ok')
    expect(loading.value).toBe(false)
    expect(error.value).toBe('')
  })

  it('wrap sets error and shows toast on failure', async () => {
    const { data, loading, error, wrap } = useLoadingState<string>()
    const result = await wrap(() => Promise.reject(new Error('Server error')), '请求失败')
    expect(result).toBeNull()
    expect(data.value).toBeNull()
    expect(loading.value).toBe(false)
    expect(error.value).toBe('Server error')
  })

  it('wrap uses fallback message for non-Error rejections', async () => {
    const { error, wrap } = useLoadingState<string>()
    await wrap(() => Promise.reject('unknown'), '自定义错误')
    expect(error.value).toBe('自定义错误')
  })

  it('reset clears all state', async () => {
    const { data, loading, error, wrap, reset } = useLoadingState<string>()
    await wrap(() => Promise.resolve('data'))
    expect(data.value).toBe('data')
    reset()
    expect(data.value).toBeNull()
    expect(loading.value).toBe(false)
    expect(error.value).toBe('')
  })

  it('wrap clears previous error on new call', async () => {
    const { error, wrap } = useLoadingState<string>()
    await wrap(() => Promise.reject(new Error('first error')))
    expect(error.value).toBe('first error')
    await wrap(() => Promise.resolve('ok'))
    expect(error.value).toBe('')
  })
})
