import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, reactive, ref } from 'vue'
import { useMarketAnomalyNotify } from './useMarketAnomalyNotify'
import type { WsMessage } from '@/stores/websocket'

const mockToast = vi.fn()

vi.mock('@/stores/websocket', () => ({
  useWebSocketStore: vi.fn(),
}))

vi.mock('@/composables/useToast', () => ({
  useToast: () => ({ toast: mockToast }),
}))

import { useWebSocketStore } from '@/stores/websocket'

function createTestComponent() {
  const storeState = reactive({
    lastMessage: null as WsMessage | null,
  })

  vi.mocked(useWebSocketStore).mockReturnValue(storeState as unknown as ReturnType<typeof useWebSocketStore>)

  const Comp = defineComponent({
    setup() {
      useMarketAnomalyNotify()
      return {}
    },
    template: '<div />',
  })

  return { Comp, storeState }
}

describe('useMarketAnomalyNotify', () => {
  beforeEach(() => {
    mockToast.mockClear()
  })

  it('shows toast on smart_alert message', async () => {
    const { Comp, storeState } = createTestComponent()
    mount(Comp)

    storeState.lastMessage = {
      type: 'smart_alert',
      data: { symbol: '600000', name: '浦发银行', alert_type: 'volume_spike', z_score: 3.5 },
      timestamp: Date.now(),
    }
    await new Promise(r => setTimeout(r, 0))

    expect(mockToast).toHaveBeenCalledWith('warning', expect.stringContaining('量能异动'))
  })

  it('shows toast on alert_triggered message', async () => {
    const { Comp, storeState } = createTestComponent()
    mount(Comp)

    storeState.lastMessage = {
      type: 'alert_triggered',
      data: { symbol: '600000', name: '浦发银行', direction: 'price_above', target_price: 10.5 },
      timestamp: Date.now(),
    }
    await new Promise(r => setTimeout(r, 0))

    expect(mockToast).toHaveBeenCalledWith('info', expect.stringContaining('价格突破'))
  })

  it('ignores non-alert message types', async () => {
    const { Comp, storeState } = createTestComponent()
    mount(Comp)

    storeState.lastMessage = {
      type: 'heartbeat',
      data: {},
      timestamp: Date.now(),
    }
    await new Promise(r => setTimeout(r, 0))

    expect(mockToast).not.toHaveBeenCalled()
  })

  it('throttles rapid notifications', async () => {
    const { Comp, storeState } = createTestComponent()
    mount(Comp)

    for (let i = 0; i < 15; i++) {
      storeState.lastMessage = {
        type: 'smart_alert',
        data: { symbol: `60000${i}`, name: `Stock${i}`, alert_type: 'volume_spike', z_score: 2.0 },
        timestamp: Date.now(),
      }
    }
    await new Promise(r => setTimeout(r, 0))

    expect(mockToast.mock.calls.length).toBeLessThan(15)
  })

  it('handles unknown alert_type gracefully', async () => {
    const { Comp, storeState } = createTestComponent()
    mount(Comp)

    storeState.lastMessage = {
      type: 'smart_alert',
      data: { symbol: '600000', name: '浦发银行', alert_type: 'unknown_type', z_score: 1.0 },
      timestamp: Date.now(),
    }
    await new Promise(r => setTimeout(r, 0))

    expect(mockToast).toHaveBeenCalledWith('info', expect.stringContaining('unknown_type'))
  })
})
