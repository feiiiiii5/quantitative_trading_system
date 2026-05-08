import { ref, onUnmounted, getCurrentScope } from 'vue'

let workerInstance: Worker | null = null
let workerRefCount = 0

function getWorker(): Worker {
  if (!workerInstance) {
    workerInstance = new Worker(
      new URL('../workers/indicator.worker.ts', import.meta.url),
      { type: 'module' }
    )
  }
  return workerInstance
}

function releaseWorker(): void {
  workerRefCount = Math.max(0, workerRefCount - 1)
  if (workerRefCount === 0 && workerInstance) {
    workerInstance.terminate()
    workerInstance = null
  }
}

interface WorkerResult {
  data: Record<string, unknown> | null
  error: string | null
  loading: boolean
}

export function useIndicatorWorker(): { result: typeof result; compute: typeof compute; cleanup: () => void } {
  const result = ref<WorkerResult>({ data: null, error: null, loading: false })
  let reqId = 0
  let activeHandler: ((e: MessageEvent) => void) | null = null
  workerRefCount++

  function cleanup(): void {
    reqId = -1
    if (activeHandler) {
      getWorker().removeEventListener('message', activeHandler)
      activeHandler = null
    }
    releaseWorker()
  }

  function compute(type: string, data: number[], params: Record<string, number> = {}) {
    if (activeHandler) {
      getWorker().removeEventListener('message', activeHandler)
      activeHandler = null
    }

    result.value = { data: null, error: null, loading: true }
    const myId = ++reqId
    const w = getWorker()

    const handler = (e: MessageEvent) => {
      if (e.data.type === type && myId === reqId) {
        w.removeEventListener('message', handler)
        activeHandler = null
        if (e.data.error) {
          result.value = { data: null, error: e.data.error as string, loading: false }
        } else {
          result.value = { data: e.data.result as Record<string, unknown>, error: null, loading: false }
        }
      }
    }

    activeHandler = handler
    w.addEventListener('message', handler)
    w.postMessage({ type, data, params })
  }

  if (getCurrentScope()) {
    onUnmounted(cleanup)
  }

  return { result, compute, cleanup }
}
