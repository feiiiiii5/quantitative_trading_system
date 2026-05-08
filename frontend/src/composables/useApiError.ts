import { ref, type Ref } from 'vue'
import { useToast } from '@/composables/useToast'

export interface UseApiErrorReturn {
  lastError: Ref<string>
  handleApiError: (e: unknown, fallbackMsg?: string) => void
  clearError: () => void
}

export function useApiError(): UseApiErrorReturn {
  const lastError = ref('')
  const { toast } = useToast()

  function handleApiError(e: unknown, fallbackMsg = '请求失败'): void {
    const msg = e instanceof Error ? e.message : fallbackMsg
    lastError.value = msg
    toast('error', msg)
  }

  function clearError(): void {
    lastError.value = ''
  }

  return { lastError, handleApiError, clearError }
}
