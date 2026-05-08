import { ref, readonly, type Ref, type ComputedRef, computed } from 'vue'
import { invalidateQuery } from './useQuery'

export interface UseMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>
  invalidateKeys?: string[]
  onSuccess?: (data: TData, variables: TVariables) => void
  onError?: (error: Error, variables: TVariables) => void
}

export interface UseMutationReturn<TData, TVariables> {
  data: Readonly<Ref<TData | null>>
  error: Readonly<Ref<Error | null>>
  isLoading: ComputedRef<boolean>
  isSuccess: ComputedRef<boolean>
  isError: ComputedRef<boolean>
  mutate: (variables: TVariables) => Promise<TData | null>
  reset: () => void
}

export function useMutation<TData, TVariables = void>(
  options: UseMutationOptions<TData, TVariables>,
): UseMutationReturn<TData, TVariables> {
  const { mutationFn, invalidateKeys = [], onSuccess, onError } = options

  const data = ref<TData | null>(null) as Ref<TData | null>
  const error = ref<Error | null>(null)
  const isLoading = ref(false)
  const status = ref<'idle' | 'loading' | 'success' | 'error'>('idle')

  const isSuccess = computed(() => status.value === 'success')
  const isError = computed(() => status.value === 'error')

  async function mutate(variables: TVariables): Promise<TData | null> {
    isLoading.value = true
    status.value = 'loading'
    error.value = null

    try {
      const result = await mutationFn(variables)
      data.value = result
      status.value = 'success'

      for (const key of invalidateKeys) {
        invalidateQuery(key)
      }

      onSuccess?.(result, variables)
      return result
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error(String(err))
      error.value = errorObj
      status.value = 'error'
      onError?.(errorObj, variables)
      return null
    } finally {
      isLoading.value = false
    }
  }

  function reset(): void {
    data.value = null
    error.value = null
    status.value = 'idle'
  }

  return {
    data: readonly(data) as Readonly<Ref<TData | null>>,
    error: readonly(error) as Readonly<Ref<Error | null>>,
    isLoading: computed(() => isLoading.value),
    isSuccess,
    isError,
    mutate,
    reset,
  }
}
