import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useApiError } from './useApiError'

vi.mock('./useToast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}))

describe('useApiError', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('handles Error instances', () => {
    const { handleApiError, lastError } = useApiError()
    handleApiError(new Error('Server error'))
    expect(lastError.value).toBe('Server error')
  })

  it('uses fallback message for non-Error values', () => {
    const { handleApiError, lastError } = useApiError()
    handleApiError('unknown', '请求失败')
    expect(lastError.value).toBe('请求失败')
  })

  it('clearError resets lastError', () => {
    const { handleApiError, lastError, clearError } = useApiError()
    handleApiError(new Error('fail'))
    expect(lastError.value).toBe('fail')
    clearError()
    expect(lastError.value).toBe('')
  })

  it('default fallback message is 请求失败', () => {
    const { handleApiError, lastError } = useApiError()
    handleApiError(null)
    expect(lastError.value).toBe('请求失败')
  })
})
