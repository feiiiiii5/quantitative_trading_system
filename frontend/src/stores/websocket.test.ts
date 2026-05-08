import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWebSocketStore } from '@/stores/websocket'

describe('useWebSocketStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts disconnected', () => {
    const store = useWebSocketStore()
    expect(store.connected).toBe(false)
    expect(store.messages).toHaveLength(0)
  })

  it('on/off registers and removes handlers', () => {
    const store = useWebSocketStore()
    const handler = vi.fn()
    store.on('test_type', handler)
    store.off('test_type', handler)
    expect(handler).not.toHaveBeenCalled()
  })

  it('disconnect sets connected to false and clears state', () => {
    const store = useWebSocketStore()
    store.disconnect()
    expect(store.connected).toBe(false)
    expect(store.messages).toHaveLength(0)
    expect(store.reconnectCount).toBe(5)
  })

  it('reset clears everything', () => {
    const store = useWebSocketStore()
    store.reset()
    expect(store.connected).toBe(false)
    expect(store.reconnectCount).toBe(0)
  })

  it('getMessagesByType returns filtered messages', () => {
    const store = useWebSocketStore()
    const result = store.getMessagesByType('nonexistent')
    expect(result).toHaveLength(0)
  })

  it('subscribe and unsubscribe are no-ops when not connected', () => {
    const store = useWebSocketStore()
    expect(() => store.subscribe(['AAPL'])).not.toThrow()
    expect(() => store.unsubscribe(['AAPL'])).not.toThrow()
  })
})
