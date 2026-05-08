import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { usePwaInstall, registerUpdateSW } from './usePwaInstall'

describe('usePwaInstall', () => {
  let cleanup: () => void

  beforeEach(() => {
    vi.stubGlobal('navigator', { onLine: true })
  })

  afterEach(() => {
    if (cleanup) cleanup()
  })

  it('initializes isOffline based on navigator.onLine', () => {
    vi.stubGlobal('navigator', { onLine: false })
    const result = usePwaInstall()
    cleanup = result.cleanup
    expect(result.isOffline.value).toBe(true)
  })

  it('sets canInstall to true on beforeinstallprompt event', () => {
    const result = usePwaInstall()
    cleanup = result.cleanup
    expect(result.canInstall.value).toBe(false)

    const event = new Event('beforeinstallprompt')
    Object.defineProperty(event, 'prompt', { value: vi.fn() })
    Object.defineProperty(event, 'userChoice', { value: Promise.resolve({ outcome: 'accepted' }) })
    Object.defineProperty(event, 'preventDefault', { value: vi.fn() })
    window.dispatchEvent(event)

    expect(result.canInstall.value).toBe(true)
  })

  it('updates isOffline on online/offline events', () => {
    const result = usePwaInstall()
    cleanup = result.cleanup
    expect(result.isOffline.value).toBe(false)

    window.dispatchEvent(new Event('offline'))
    expect(result.isOffline.value).toBe(true)

    window.dispatchEvent(new Event('online'))
    expect(result.isOffline.value).toBe(false)
  })

  it('applyUpdate calls registered updateSW', () => {
    const mockUpdate = vi.fn().mockResolvedValue(undefined)
    registerUpdateSW(mockUpdate)

    const result = usePwaInstall()
    cleanup = result.cleanup
    result.applyUpdate()

    expect(mockUpdate).toHaveBeenCalledWith(true)
  })

  it('promptInstall does nothing without deferred prompt', async () => {
    const result = usePwaInstall()
    cleanup = result.cleanup
    expect(result.canInstall.value).toBe(false)
    await result.promptInstall()
    expect(result.canInstall.value).toBe(false)
  })

  it('cleanup removes event listeners', () => {
    const result = usePwaInstall()
    const removeSpy = vi.spyOn(window, 'removeEventListener')

    result.cleanup()
    expect(removeSpy).toHaveBeenCalledWith('beforeinstallprompt', expect.any(Function))
    expect(removeSpy).toHaveBeenCalledWith('online', expect.any(Function))
    expect(removeSpy).toHaveBeenCalledWith('offline', expect.any(Function))

    removeSpy.mockRestore()
  })
})
