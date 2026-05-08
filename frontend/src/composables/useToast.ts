import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
}

const toasts = ref<ToastItem[]>([])
let nextId = 0

const TOAST_DISPLAY_MS = 3_000

export function useToast(): { toast: (type: ToastType, message: string) => void; toasts: typeof toasts } {
  function toast(type: ToastType, message: string) {
    const id = ++nextId
    toasts.value = [...toasts.value, { id, type, message }]
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, TOAST_DISPLAY_MS)
  }

  return { toast, toasts }
}
