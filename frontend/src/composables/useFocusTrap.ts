import { onMounted, onUnmounted, ref, type Ref } from 'vue'

export interface UseFocusTrapOptions {
  escapeDeactivates?: boolean
  initialFocus?: string
}

export function useFocusTrap(
  containerRef: Ref<HTMLElement | null>,
  options: UseFocusTrapOptions = {},
): { activate: () => void; deactivate: () => void; isActive: Ref<boolean> } {
  const { escapeDeactivates = true, initialFocus } = options
  const isActive = ref(false)
  let previouslyFocused: HTMLElement | null = null

  const FOCUSABLE = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
  ].join(', ')

  function getFocusableElements(): HTMLElement[] {
    if (!containerRef.value) return []
    return Array.from(containerRef.value.querySelectorAll<HTMLElement>(FOCUSABLE))
  }

  function onKeyDown(e: KeyboardEvent): void {
    if (e.key === 'Tab') handleTab(e)
    if (e.key === 'Escape' && escapeDeactivates) deactivate()
  }

  function handleTab(e: KeyboardEvent): void {
    const focusable = getFocusableElements()
    if (focusable.length === 0) return

    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    const active = document.activeElement

    if (e.shiftKey) {
      if (active === first || !containerRef.value?.contains(active)) {
        e.preventDefault()
        last.focus()
      }
    } else {
      if (active === last || !containerRef.value?.contains(active)) {
        e.preventDefault()
        first.focus()
      }
    }
  }

  function activate(): void {
    previouslyFocused = document.activeElement as HTMLElement
    isActive.value = true
    document.addEventListener('keydown', onKeyDown)

    if (initialFocus) {
      const el = containerRef.value?.querySelector<HTMLElement>(initialFocus)
      if (el) el.focus()
    } else {
      const focusable = getFocusableElements()
      if (focusable.length > 0) focusable[0].focus()
    }
  }

  function deactivate(): void {
    isActive.value = false
    document.removeEventListener('keydown', onKeyDown)
    if (previouslyFocused && previouslyFocused.focus) {
      previouslyFocused.focus()
      previouslyFocused = null
    }
  }

  onUnmounted(() => {
    if (isActive.value) deactivate()
  })

  return { activate, deactivate, isActive }
}
