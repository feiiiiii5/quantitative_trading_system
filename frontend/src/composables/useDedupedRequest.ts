const pendingRequests = new Map<string, Promise<unknown>>()

const DEDUP_TTL_MS = 5_000

function dedupKey(url: string, params?: Record<string, unknown>): string {
  return `${url}::${JSON.stringify(params ?? {})}`
}

export function dedupedRequest<T>(
  key: string,
  fetcher: () => Promise<T>,
): Promise<T> {
  const existing = pendingRequests.get(key)
  if (existing) {
    return existing as Promise<T>
  }

  const promise = fetcher().finally(() => {
    setTimeout(() => pendingRequests.delete(key), DEDUP_TTL_MS)
  })

  pendingRequests.set(key, promise)
  return promise
}

export function createDedupedGetter<T>(
  url: string,
  fetcher: (url: string, params?: Record<string, unknown>, signal?: AbortSignal, cacheTtl?: number) => Promise<T>,
) {
  return (params?: Record<string, unknown>, signal?: AbortSignal, cacheTtl?: number): Promise<T> => {
    const key = dedupKey(url, params)
    return dedupedRequest(key, () => fetcher(url, params, signal, cacheTtl))
  }
}

export function clearDedupCache(): void {
  pendingRequests.clear()
}

export function getPendingCount(): number {
  return pendingRequests.size
}
