import { defineStore } from 'pinia'
import { ref, shallowRef, triggerRef } from 'vue'
import { createLogger } from '@/composables/useLogger'

const log = createLogger('WebSocket')

export interface WsMessage {
  type: string
  data: Record<string, unknown>
  timestamp: number
}

type WsHandler = (data: Record<string, unknown>) => void

export const useWebSocketStore = defineStore('websocket', () => {
  const connected = ref(false)
  const ws = ref<WebSocket | null>(null)
  const lastMessage = ref<WsMessage | null>(null)
  const messages = shallowRef<WsMessage[]>([])
  const reconnectCount = ref(0)
  const WS_RECONNECT_BASE_MS = 1_000
  const WS_RECONNECT_JITTER_MS = 500
  const WS_MESSAGE_BUFFER_MAX = 100
  const WS_MESSAGE_BUFFER_KEEP = 50
  const MAX_RECONNECT_ATTEMPTS = 5
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let intentionalClose = false

  const _handlers: Record<string, WsHandler[]> = {}

  function on(type: string, cb: WsHandler): void {
    if (!_handlers[type]) _handlers[type] = []
    _handlers[type].push(cb)
  }

  function off(type: string, cb: WsHandler): void {
    const list = _handlers[type]
    if (!list) return
    const idx = list.indexOf(cb)
    if (idx >= 0) list.splice(idx, 1)
    if (list.length === 0) delete _handlers[type]
  }

  function connect(url: string = `ws://${window.location.host}/api/ws`) {
    if (ws.value?.readyState === WebSocket.OPEN || ws.value?.readyState === WebSocket.CONNECTING) return

    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }

    intentionalClose = false
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      connected.value = true
      reconnectCount.value = 0
    }

    ws.value.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        const msg: WsMessage = {
          type: parsed.type || 'unknown',
          data: parsed.data || parsed,
          timestamp: Date.now(),
        }
        lastMessage.value = msg
        const updated = [...messages.value, msg]
        if (updated.length > WS_MESSAGE_BUFFER_MAX) {
          messages.value = updated.slice(-WS_MESSAGE_BUFFER_KEEP)
        } else {
          messages.value = updated
        }
        triggerRef(messages)

        const handlers = _handlers[msg.type]
        if (handlers) {
          for (const h of handlers) {
            try { h(msg.data) } catch (e) { log.warn('handler error', e) }
          }
        }
      } catch (err) {
        log.warn('message parse failed', err)
      }
    }

    ws.value.onclose = () => {
      connected.value = false
      ws.value = null
      if (!intentionalClose && reconnectCount.value < MAX_RECONNECT_ATTEMPTS) {
        reconnectCount.value++
        const jitter = Math.random() * WS_RECONNECT_JITTER_MS
        const delay = WS_RECONNECT_BASE_MS * reconnectCount.value + jitter
        reconnectTimer = setTimeout(() => connect(url), delay)
      }
    }

    ws.value.onerror = () => {
      log.error('connection error')
      connected.value = false
      ws.value?.close()
    }
  }

  function disconnect() {
    intentionalClose = true
    reconnectCount.value = MAX_RECONNECT_ATTEMPTS
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws.value?.close()
    ws.value = null
    connected.value = false
    messages.value = []
    lastMessage.value = null
  }

  function subscribe(symbols: string[]) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'subscribe', symbols }))
    }
  }

  function unsubscribe(symbols: string[]) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ type: 'unsubscribe', symbols }))
    }
  }

  function getMessagesByType(type: string): WsMessage[] {
    return messages.value.filter(m => m.type === type)
  }

  function reset() {
    disconnect()
    reconnectCount.value = 0
  }

  return {
    connected,
    lastMessage,
    messages,
    reconnectCount,
    connect,
    disconnect,
    reset,
    subscribe,
    unsubscribe,
    getMessagesByType,
    on,
    off,
  }
})
