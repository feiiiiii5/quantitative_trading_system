import { ref, shallowRef } from 'vue'

const workerRef = shallowRef<Worker | null>(null)
const computing = ref(false)

function getWorker(): Worker {
  if (!workerRef.value) {
    workerRef.value = new Worker(
      new URL('../workers/indicator.worker.ts', import.meta.url),
      { type: 'module' }
    )
  }
  return workerRef.value
}

export function useIndicatorWorker() {
  function compute(type: string, data: { close: number[]; high?: number[]; low?: number[]; volume?: number[] }): Promise<any> {
    return new Promise((resolve) => {
      computing.value = true
      const worker = getWorker()
      const handler = (e: MessageEvent) => {
        if (e.data.type === type) {
          worker.removeEventListener('message', handler)
          computing.value = false
          resolve(e.data.result)
        }
      }
      worker.addEventListener('message', handler)
      worker.postMessage({ type, data })
    })
  }

  function terminate() {
    if (workerRef.value) {
      workerRef.value.terminate()
      workerRef.value = null
    }
  }

  return { compute, computing, terminate }
}
