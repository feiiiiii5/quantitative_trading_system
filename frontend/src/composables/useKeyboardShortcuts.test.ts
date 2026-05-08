import { describe, it, expect, vi, beforeEach } from 'vitest'
import { registerGlobalShortcut, registerNavigationShortcuts, _resetState, getRegisteredShortcuts } from './useKeyboardShortcuts'

function fireKey(key: string, opts: Partial<KeyboardEventInit> = {}): void {
  const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...opts })
  window.dispatchEvent(event)
}

describe('useKeyboardShortcuts', () => {
  beforeEach(() => {
    _resetState()
  })

  describe('registerGlobalShortcut', () => {
    it('invokes handler when key matches', () => {
      const handler = vi.fn()
      registerGlobalShortcut({ key: 'k', handler })

      fireKey('k')
      expect(handler).toHaveBeenCalledTimes(1)
    })

    it('does not invoke handler on non-matching key', () => {
      const handler = vi.fn()
      registerGlobalShortcut({ key: 'k', handler })

      fireKey('j')
      expect(handler).not.toHaveBeenCalled()
    })

    it('matches key case-insensitively', () => {
      const handler = vi.fn()
      registerGlobalShortcut({ key: 'K', handler })

      fireKey('k')
      expect(handler).toHaveBeenCalledTimes(1)
    })

    it('requires ctrl/meta when ctrl flag is set', () => {
      const handler = vi.fn()
      registerGlobalShortcut({ key: 'k', ctrl: true, handler })

      fireKey('k')
      expect(handler).not.toHaveBeenCalled()

      fireKey('k', { ctrlKey: true })
      expect(handler).toHaveBeenCalledTimes(1)
    })

    it('requires shift when shift flag is set', () => {
      const handler = vi.fn()
      registerGlobalShortcut({ key: 'k', shift: true, handler })

      fireKey('k')
      expect(handler).not.toHaveBeenCalled()

      fireKey('k', { shiftKey: true })
      expect(handler).toHaveBeenCalledTimes(1)
    })

    it('unregister function removes the shortcut', () => {
      const handler = vi.fn()
      const unregister = registerGlobalShortcut({ key: 'k', handler })

      unregister()
      fireKey('k')
      expect(handler).not.toHaveBeenCalled()
    })

    it('handler receives preventDefault call via event argument', () => {
      const handler = vi.fn((e?: KeyboardEvent) => {
        e?.preventDefault()
      })
      registerGlobalShortcut({ key: 'k', handler })

      fireKey('k')
      expect(handler).toHaveBeenCalledTimes(1)
    })

    it('does not call handler on non-matching event', () => {
      const handler = vi.fn()
      registerGlobalShortcut({ key: 'k', handler })

      fireKey('j')
      expect(handler).not.toHaveBeenCalled()
    })
  })

  describe('listener lifecycle', () => {
    it('removes window listener after all shortcuts unregistered', () => {
      const removeSpy = vi.spyOn(window, 'removeEventListener')
      const unregister = registerGlobalShortcut({ key: 'x', handler: vi.fn() })

      unregister()
      expect(removeSpy).toHaveBeenCalledWith('keydown', expect.any(Function))

      removeSpy.mockRestore()
    })

    it('does not remove listener while other shortcuts remain', () => {
      const removeSpy = vi.spyOn(window, 'removeEventListener')
      const unregister1 = registerGlobalShortcut({ key: 'a', handler: vi.fn() })
      registerGlobalShortcut({ key: 'b', handler: vi.fn() })

      unregister1()
      expect(removeSpy).not.toHaveBeenCalledWith('keydown', expect.any(Function))

      removeSpy.mockRestore()
    })
  })

  describe('registerNavigationShortcuts', () => {
    it('registers Alt+1 through Alt+5 navigation shortcuts', () => {
      const routerPush = vi.fn()
      registerNavigationShortcuts(routerPush)

      fireKey('1', { altKey: true })
      expect(routerPush).toHaveBeenCalledWith('/')

      fireKey('2', { altKey: true })
      expect(routerPush).toHaveBeenCalledWith('/market')

      fireKey('3', { altKey: true })
      expect(routerPush).toHaveBeenCalledWith('/strategy')

      fireKey('4', { altKey: true })
      expect(routerPush).toHaveBeenCalledWith('/portfolio')

      fireKey('5', { altKey: true })
      expect(routerPush).toHaveBeenCalledWith('/watchlist')
    })

    it('does not navigate without Alt key', () => {
      const routerPush = vi.fn()
      registerNavigationShortcuts(routerPush)

      fireKey('1')
      expect(routerPush).not.toHaveBeenCalled()
    })

    it('unregister removes all navigation shortcuts', () => {
      const routerPush = vi.fn()
      const unregister = registerNavigationShortcuts(routerPush)

      unregister()
      fireKey('1', { altKey: true })
      expect(routerPush).not.toHaveBeenCalled()
    })

    it('adds shortcuts to getRegisteredShortcuts', () => {
      registerNavigationShortcuts(vi.fn())

      const shortcuts = getRegisteredShortcuts()
      const navKeys = shortcuts.filter(s => s.alt && ['1','2','3','4','5'].includes(s.key))
      expect(navKeys.length).toBe(5)
    })
  })
})
