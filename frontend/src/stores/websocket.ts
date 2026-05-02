import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface WsMessage {
  type: string
  data: any
  timestamp: number
}

export const useWebSocketStore = defineStore('websocket', () => {
  const connected = ref(false)
  const ws = ref<WebSocket | null>(null)
  const lastMessage = ref<WsMessage | null>(null)
  const messages = ref<WsMessage[]>([])
  const reconnectCount = ref(0)
  const maxReconnect = 5

  function connect(url: string = `ws://${window.location.host}/api/ws`) {
    if (ws.value?.readyState === WebSocket.OPEN) return

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
        messages.value.push(msg)
        if (messages.value.length > 100) {
          messages.value = messages.value.slice(-50)
        }
      } catch {}
    }

    ws.value.onclose = () => {
      connected.value = false
      if (reconnectCount.value < maxReconnect) {
        reconnectCount.value++
        setTimeout(() => connect(url), 1000 * reconnectCount.value)
      }
    }

    ws.value.onerror = () => {
      connected.value = false
    }
  }

  function disconnect() {
    reconnectCount.value = maxReconnect
    ws.value?.close()
    ws.value = null
    connected.value = false
  }

  function subscribe(channel: string) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ action: 'subscribe', channel }))
    }
  }

  function unsubscribe(channel: string) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({ action: 'unsubscribe', channel }))
    }
  }

  function getMessagesByType(type: string): WsMessage[] {
    return messages.value.filter(m => m.type === type)
  }

  return {
    connected,
    lastMessage,
    messages,
    reconnectCount,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    getMessagesByType,
  }
})
