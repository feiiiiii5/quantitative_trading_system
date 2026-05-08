import { onUnmounted, getCurrentScope } from 'vue'

export function useRequestCancel(): { createSignal: () => AbortSignal; cancelAll: () => void } {
  const controllers: AbortController[] = []

  function createSignal(): AbortSignal {
    const controller = new AbortController()
    controllers.push(controller)
    controller.signal.addEventListener('abort', () => {
      const idx = controllers.indexOf(controller)
      if (idx !== -1) controllers.splice(idx, 1)
    }, { once: true })
    return controller.signal
  }

  function cancelAll(): void {
    const pending = [...controllers]
    controllers.length = 0
    for (const controller of pending) {
      controller.abort()
    }
  }

  if (getCurrentScope()) {
    onUnmounted(cancelAll)
  }

  return { createSignal, cancelAll }
}
