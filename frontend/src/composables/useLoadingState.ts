import { ref, type Ref } from 'vue'
import { useToast } from '@/composables/useToast'

export interface UseLoadingStateReturn<T> {
  data: Ref<T | null>
  loading: Ref<boolean>
  error: Ref<string>
  wrap: (fn: () => Promise<T>, errorMsg?: string) => Promise<T | null>
  reset: () => void
}

export function useLoadingState<T>(): UseLoadingStateReturn<T> {
  const data = ref<T | null>(null) as Ref<T | null>
  const loading = ref(false)
  const error = ref('')

  const { toast } = useToast()

  async function wrap(fn: () => Promise<T>, errorMsg = '请求失败'): Promise<T | null> {
    loading.value = true
    error.value = ''
    try {
      const result = await fn()
      data.value = result
      return result
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : errorMsg
      error.value = msg
      toast('error', msg)
      return null
    } finally {
      loading.value = false
    }
  }

  function reset(): void {
    data.value = null
    loading.value = false
    error.value = ''
  }

  return { data, loading, error, wrap, reset }
}
