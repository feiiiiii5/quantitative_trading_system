import { ref } from 'vue'

interface ToastItem {
  id: number
  message: string
  type: 'success' | 'warning' | 'error' | 'info'
  duration: number
}

const toasts = ref<ToastItem[]>([])
let _nextId = 0

function show(message: string, type: ToastItem['type'] = 'info', duration = 3000) {
  const id = _nextId++
  toasts.value.push({ id, message, type, duration })
  if (duration > 0) {
    setTimeout(() => remove(id), duration)
  }
}

function remove(id: number) {
  const idx = toasts.value.findIndex(t => t.id === id)
  if (idx !== -1) toasts.value.splice(idx, 1)
}

function success(message: string) { show(message, 'success') }
function warning(message: string) { show(message, 'warning', 5000) }
function error(message: string) { show(message, 'error', 5000) }
function info(message: string) { show(message, 'info') }

export function useToast() {
  return { toasts, show, remove, success, warning, error, info }
}
