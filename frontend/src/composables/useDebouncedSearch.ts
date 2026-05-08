import { ref, watch, onUnmounted, type Ref } from 'vue'
import { createLogger } from '@/composables/useLogger'

const log = createLogger('DebouncedSearch')

export interface UseDebouncedSearchReturn {
  query: Ref<string>
  loading: Ref<boolean>
}

export function useDebouncedSearch(
  searchFn: (query: string) => Promise<void>,
  delay = 300,
): UseDebouncedSearchReturn {
  const query = ref('')
  const loading = ref(false)
  let timer: ReturnType<typeof setTimeout> | undefined

  watch(query, (newVal) => {
    if (timer) clearTimeout(timer)
    if (!newVal.trim()) {
      loading.value = false
      return
    }
    loading.value = true
    timer = setTimeout(async () => {
      try {
        await searchFn(newVal.trim())
      } catch (e) {
        log.warn('Search failed', e)
      } finally {
        loading.value = false
      }
    }, delay)
  })

  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  return { query, loading }
}
