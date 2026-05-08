import { onMounted, onUnmounted, ref, getCurrentScope } from 'vue'

export interface UsePollingOptions {
  immediate?: boolean
  interval?: number
}

export function usePolling(
  fn: () => Promise<void> | void,
  options: UsePollingOptions = {},
) {
  const { immediate = true, interval = 30_000 } = options
  const isActive = ref(false)
  let timer: ReturnType<typeof setTimeout> | null = null
  let stopped = false

  async function tick() {
    if (stopped) return
    try {
      await fn()
    } finally {
      if (!stopped) {
        timer = setTimeout(tick, interval)
      }
    }
  }

  function start() {
    stop()
    stopped = false
    isActive.value = true
    timer = setTimeout(tick, interval)
  }

  function stop() {
    stopped = true
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
    isActive.value = false
  }

  async function execute() {
    await fn()
  }

  function init() {
    if (immediate) {
      fn()
    }
    start()
  }

  if (getCurrentScope()) {
    onMounted(init)
    onUnmounted(stop)
  } else {
    init()
  }

  return { isActive, start, stop, execute }
}
