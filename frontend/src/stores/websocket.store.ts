import { defineStore } from 'pinia'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    connected: false,
    subscriptions: new Set<string>(),
    lastMessage: null as any,
    _ws: null as WebSocket | null,
    _reconnectAttempts: 0,
    _maxReconnectDelay: 30000,
    _heartbeatTimer: null as any,
    _reconnectTimer: null as any,
    _messageQueue: [] as any[],
    seq: 0,
  }),
  actions: {
    connect() {
      if (this._ws && this._ws.readyState === WebSocket.OPEN) return

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${protocol}//${window.location.host}/api/ws/realtime`

      const ws = new WebSocket(url)

      ws.onopen = () => {
        this.connected = true
        this._reconnectAttempts = 0
        this._startHeartbeat()
        this._flushMessageQueue()
        if (this.subscriptions.size > 0) {
          this._send({ type: 'subscribe', symbols: Array.from(this.subscriptions) })
        }
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.lastMessage = data
          this.seq = data.seq || this.seq + 1
          this._handleMessage(data)
        } catch (e) {
          console.error('WS message parse error:', e)
        }
      }

      ws.onclose = () => {
        this.connected = false
        this._stopHeartbeat()
        this._scheduleReconnect()
      }

      ws.onerror = () => {
        this.connected = false
      }

      this._ws = ws
    },

    disconnect() {
      this._stopHeartbeat()
      this._cancelReconnect()
      if (this._ws) {
        this._ws.close()
        this._ws = null
      }
      this.connected = false
    },

    subscribe(symbols: string[]) {
      symbols.forEach(s => this.subscriptions.add(s))
      this._send({ type: 'subscribe', symbols })
    },

    unsubscribe(symbols: string[]) {
      symbols.forEach(s => this.subscriptions.delete(s))
      this._send({ type: 'unsubscribe', symbols })
    },

    _send(data: any) {
      if (this._ws && this._ws.readyState === WebSocket.OPEN) {
        this._ws.send(JSON.stringify(data))
      } else {
        this._messageQueue.push(data)
      }
    },

    _flushMessageQueue() {
      while (this._messageQueue.length > 0) {
        const msg = this._messageQueue.shift()
        this._send(msg)
      }
    },

    _startHeartbeat() {
      this._stopHeartbeat()
      this._heartbeatTimer = window.setInterval(() => {
        if (this._ws && this._ws.readyState === WebSocket.OPEN) {
          this._ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    },

    _stopHeartbeat() {
      if (this._heartbeatTimer) {
        clearInterval(this._heartbeatTimer)
        this._heartbeatTimer = null
      }
    },

    _scheduleReconnect() {
      if (this._reconnectAttempts >= 20) return
      const delay = Math.min(1000 * Math.pow(2, this._reconnectAttempts), this._maxReconnectDelay)
      this._reconnectAttempts++
      this._reconnectTimer = setTimeout(() => {
        this._reconnectTimer = null
        this.connect()
      }, delay)
    },

    _cancelReconnect() {
      if (this._reconnectTimer) {
        clearTimeout(this._reconnectTimer)
        this._reconnectTimer = null
      }
      this._reconnectAttempts = 0
    },

    _handleMessage(data: any) {
      if (data.type === 'quote_update') {
        // 实时行情更新 - 通过 lastMessage 传递给各组件消费
        // Dashboard.vue 等组件已通过 watch(lastMessage) 处理此消息
      }

      if (data.type === 'signal') {
        const { symbol, strategy, signal_type, score, price } = data.data || data
        const direction = signal_type === 'buy' ? '买入' : signal_type === 'sell' ? '卖出' : '信号'
        const msg = `${strategy} 在 ${symbol} 产生${direction}信号 | 当前价格: ${price}`

        if ('Notification' in window) {
          if (Notification.permission === 'granted') {
            new Notification('QuantCore 策略信号', { body: msg })
          } else if (Notification.permission !== 'denied') {
            Notification.requestPermission().then(perm => {
              if (perm === 'granted') {
                new Notification('QuantCore 策略信号', { body: msg })
              }
            })
          }
        }
      }

      if (data.type === 'alert') {
        const { symbol, alert_type, value, current_price } = data.data || data
        const msg = `${symbol} 预警触发: ${alert_type} ${value}, 当前价: ${current_price}`

        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('QuantCore 价格预警', { body: msg })
        }
      }

      if (data.type === 'market_event') {
        // 市场事件通知 - 通过 lastMessage 传递给各组件消费
      }
    },
  },
})
