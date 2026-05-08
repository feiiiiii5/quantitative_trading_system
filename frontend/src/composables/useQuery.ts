import { ref, computed, watch, onScopeDispose, getCurrentScope, readonly, type Ref, type ComputedRef } from 'vue'

export interface UseQueryOptions<T> {
  key: string
  fetcher: () => Promise<T>
  staleTime?: number
  gcTime?: number
  refetchOnWindowFocus?: boolean
  refetchOnReconnect?: boolean
  enabled?: Ref<boolean> | ComputedRef<boolean> | boolean
}

export interface UseQueryReturn<T> {
  data: Readonly<Ref<T | null>>
  error: Readonly<Ref<Error | null>>
  isLoading: ComputedRef<boolean>
  isFetching: ComputedRef<boolean>
  isStale: ComputedRef<boolean>
  refetch: () => Promise<T | null>
}

interface CacheEntry<T> {
  data: T | null
  error: Error | null
  timestamp: number
  fetchCount: number
  fetchPromise: Promise<T | null> | null
  gcTimer: ReturnType<typeof setTimeout> | null
}

const queryCache = new Map<string, CacheEntry<unknown>>()
const subscribers = new Map<string, Set<() => void>>()

const DEFAULT_STALE_TIME = 30_000
const DEFAULT_GC_TIME = 5 * 60_000

function getEntry<T>(key: string): CacheEntry<T> {
  let entry = queryCache.get(key) as CacheEntry<T> | undefined
  if (!entry) {
    entry = { data: null, error: null, timestamp: 0, fetchCount: 0, fetchPromise: null, gcTimer: null }
    queryCache.set(key, entry as CacheEntry<unknown>)
  }
  return entry
}

function notifySubscribers(key: string): void {
  const subs = subscribers.get(key)
  if (subs) {
    for (const cb of subs) cb()
  }
}

function scheduleGc(key: string, gcTime: number): void {
  const entry = queryCache.get(key)
  if (!entry) return
  if (entry.gcTimer) clearTimeout(entry.gcTimer)
  const hasSubs = (subscribers.get(key)?.size ?? 0) > 0
  if (hasSubs) return
  entry.gcTimer = setTimeout(() => {
    if ((subscribers.get(key)?.size ?? 0) === 0) {
      queryCache.delete(key)
      subscribers.delete(key)
    }
  }, gcTime)
}

export function useQuery<T>(options: UseQueryOptions<T>): UseQueryReturn<T> {
  const {
    key,
    fetcher,
    staleTime = DEFAULT_STALE_TIME,
    gcTime = DEFAULT_GC_TIME,
    refetchOnWindowFocus = true,
    refetchOnReconnect = true,
    enabled = true,
  } = options

  const data = ref<T | null>(null) as Ref<T | null>
  const error = ref<Error | null>(null)
  const isFetching = ref(false)
  const fetchCount = ref(0)
  const fetchedAt = ref(0)

  const isEnabled = computed(() => {
    if (typeof enabled === 'boolean') return enabled
    return enabled.value
  })

  const isLoading = computed(() => isFetching.value && fetchCount.value === 0)
  const isStale = computed(() => {
    if (fetchedAt.value === 0) return true
    return Date.now() - fetchedAt.value > staleTime
  })

  async function fetchQuery(): Promise<T | null> {
    if (!isEnabled.value) return null

    const entry = getEntry<T>(key)

    if (entry.fetchPromise) {
      return entry.fetchPromise as Promise<T | null>
    }

    if (!isStale.value && entry.data !== null) {
      data.value = entry.data
      error.value = entry.error
      return entry.data
    }

    isFetching.value = true

    const promise = (async () => {
      try {
        const result = await fetcher()
        const e = getEntry<T>(key)
        e.data = result
        e.error = null
        e.timestamp = Date.now()
        e.fetchCount++
        data.value = result
        error.value = null
        fetchCount.value = e.fetchCount
        fetchedAt.value = e.timestamp
        notifySubscribers(key)
        return result
      } catch (err) {
        const e = getEntry<T>(key)
        e.error = err instanceof Error ? err : new Error(String(err))
        error.value = e.error
        notifySubscribers(key)
        return null
      } finally {
        isFetching.value = false
        const e = queryCache.get(key) as CacheEntry<T> | undefined
        if (e) e.fetchPromise = null
      }
    })()

    entry.fetchPromise = promise
    return promise
  }

  function onCacheChange(): void {
    const entry = queryCache.get(key) as CacheEntry<T> | undefined
    if (entry && entry.data !== data.value) {
      data.value = entry.data
    }
    if (entry && entry.error !== error.value) {
      error.value = entry.error
    }
    if (entry && entry.timestamp !== fetchedAt.value) {
      fetchedAt.value = entry.timestamp
    }
  }

  let subscribed = false

  function subscribe(): void {
    if (subscribed) return
    subscribed = true
    let subs = subscribers.get(key)
    if (!subs) {
      subs = new Set()
      subscribers.set(key, subs)
    }
    subs.add(onCacheChange)
  }

  function unsubscribe(): void {
    if (!subscribed) return
    subscribed = false
    const subs = subscribers.get(key)
    if (subs) {
      subs.delete(onCacheChange)
      if (subs.size === 0) {
        scheduleGc(key, gcTime)
      }
    }
  }

  function onFocus(): void {
    if (refetchOnWindowFocus && isEnabled.value && isStale.value) {
      fetchQuery()
    }
  }

  function onOnline(): void {
    if (refetchOnReconnect && isEnabled.value) {
      fetchQuery()
    }
  }

  const existingEntry = queryCache.get(key) as CacheEntry<T> | undefined
  if (existingEntry && existingEntry.data !== null) {
    data.value = existingEntry.data
    error.value = existingEntry.error
    fetchCount.value = existingEntry.fetchCount
    fetchedAt.value = existingEntry.timestamp
  }

  subscribe()

  if (isEnabled.value) {
    if (!existingEntry || existingEntry.timestamp === 0 || isStale.value) {
      fetchQuery()
    }
  }

  watch(isEnabled, (newVal) => {
    if (newVal) {
      fetchQuery()
    }
  })

  if (typeof window !== 'undefined') {
    window.addEventListener('focus', onFocus)
    window.addEventListener('online', onOnline)
  }

  function cleanup(): void {
    unsubscribe()
    if (typeof window !== 'undefined') {
      window.removeEventListener('focus', onFocus)
      window.removeEventListener('online', onOnline)
    }
  }

  if (getCurrentScope()) {
    onScopeDispose(cleanup)
  }

  return {
    data: readonly(data) as Readonly<Ref<T | null>>,
    error: readonly(error) as Readonly<Ref<Error | null>>,
    isLoading,
    isFetching: computed(() => isFetching.value),
    isStale,
    refetch: fetchQuery,
  }
}

export function invalidateQuery(keyPrefix: string): void {
  for (const [key, entry] of queryCache) {
    if (key.startsWith(keyPrefix)) {
      entry.timestamp = 0
      notifySubscribers(key)
    }
  }
}

export function setQueryData<T>(key: string, data: T): void {
  const entry = getEntry<T>(key)
  entry.data = data
  entry.error = null
  entry.timestamp = Date.now()
  notifySubscribers(key)
}

export function clearQueryCache(): void {
  for (const [, entry] of queryCache) {
    if (entry.gcTimer) clearTimeout(entry.gcTimer)
  }
  queryCache.clear()
  for (const [, subs] of subscribers) {
    subs.clear()
  }
  subscribers.clear()
}

export function getCacheSize(): number {
  return queryCache.size
}
