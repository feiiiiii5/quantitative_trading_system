import { onMounted, onUnmounted } from 'vue'

type KeyHandler = (e: KeyboardEvent) => void

interface KeyBinding {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  handler: KeyHandler
  description: string
}

const bindings: KeyBinding[] = []

function matches(e: KeyboardEvent, binding: KeyBinding): boolean {
  if (e.key.toLowerCase() !== binding.key.toLowerCase()) return false
  if (binding.ctrl && !e.ctrlKey) return false
  if (binding.meta && !e.metaKey) return false
  if (binding.shift && !e.shiftKey) return false
  return true
}

function handleKeyDown(e: KeyboardEvent) {
  if ((e.target as HTMLElement)?.tagName === 'INPUT' || (e.target as HTMLElement)?.tagName === 'TEXTAREA') return
  for (const binding of bindings) {
    if (matches(e, binding)) {
      e.preventDefault()
      binding.handler(e)
      return
    }
  }
}

export function useKeyboard() {
  function register(key: string, handler: KeyHandler, description = '', opts: { ctrl?: boolean; meta?: boolean; shift?: boolean } = {}) {
    bindings.push({ key, handler, description, ...opts })
  }

  function unregister(key: string) {
    const idx = bindings.findIndex(b => b.key === key)
    if (idx >= 0) bindings.splice(idx, 1)
  }

  onMounted(() => document.addEventListener('keydown', handleKeyDown))
  onUnmounted(() => document.removeEventListener('keydown', handleKeyDown))

  return { register, unregister, bindings }
}
