import { ref, onMounted, onUnmounted, getCurrentScope } from 'vue'
import type { Ref } from 'vue'
import type { BeforeInstallPromptEvent } from '@/types/pwa'

export interface UsePwaInstallReturn {
  canInstall: Ref<boolean>
  isOffline: Ref<boolean>
  needsUpdate: Ref<boolean>
  applyUpdate: () => void
  promptInstall: () => Promise<void>
  cleanup: () => void
}

let _deferredPrompt: BeforeInstallPromptEvent | null = null
let _updateSW: ((reloadPage?: boolean) => Promise<void>) | null = null

export function usePwaInstall(): UsePwaInstallReturn {
  const canInstall = ref(false)
  const isOffline = ref(!navigator.onLine)
  const needsUpdate = ref(false)

  function onBeforeInstallPrompt(e: Event): void {
    e.preventDefault()
    _deferredPrompt = e as BeforeInstallPromptEvent
    canInstall.value = true
  }

  function onOnline(): void { isOffline.value = false }
  function onOffline(): void { isOffline.value = true }

  async function promptInstall(): Promise<void> {
    if (!_deferredPrompt) return
    _deferredPrompt.prompt()
    const { outcome } = await _deferredPrompt.userChoice
    if (outcome === 'accepted') {
      canInstall.value = false
    }
    _deferredPrompt = null
  }

  function applyUpdate(): void {
    if (_updateSW) {
      _updateSW(true)
    }
  }

  function addListeners(): void {
    window.addEventListener('beforeinstallprompt', onBeforeInstallPrompt)
    window.addEventListener('online', onOnline)
    window.addEventListener('offline', onOffline)
  }

  function cleanup(): void {
    window.removeEventListener('beforeinstallprompt', onBeforeInstallPrompt)
    window.removeEventListener('online', onOnline)
    window.removeEventListener('offline', onOffline)
  }

  if (getCurrentScope()) {
    onMounted(addListeners)
    onUnmounted(cleanup)
  } else {
    addListeners()
  }

  return { canInstall, isOffline, needsUpdate, applyUpdate, promptInstall, cleanup }
}

export function registerUpdateSW(updateSW: (reloadPage?: boolean) => Promise<void>): void {
  _updateSW = updateSW
}
