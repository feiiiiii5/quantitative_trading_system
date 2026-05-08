import { describe, it, expect } from 'vitest'

import { useRequestCancel } from './useRequestCancel'

describe('useRequestCancel', () => {
  it('creates an AbortSignal', () => {
    const { createSignal } = useRequestCancel()
    const signal = createSignal()
    expect(signal).toBeInstanceOf(AbortSignal)
    expect(signal.aborted).toBe(false)
  })

  it('cancelAll aborts all signals', () => {
    const { createSignal, cancelAll } = useRequestCancel()
    const signal1 = createSignal()
    const signal2 = createSignal()
    cancelAll()
    expect(signal1.aborted).toBe(true)
    expect(signal2.aborted).toBe(true)
  })

  it('creates independent signals across separate instances', () => {
    const instance1 = useRequestCancel()
    const instance2 = useRequestCancel()
    const s1 = instance1.createSignal()
    const s2 = instance2.createSignal()
    instance1.cancelAll()
    expect(s1.aborted).toBe(true)
    expect(s2.aborted).toBe(false)
  })

  it('does not register onUnmounted outside component scope', () => {
    const { createSignal, cancelAll } = useRequestCancel()
    createSignal()
    cancelAll()
  })
})
