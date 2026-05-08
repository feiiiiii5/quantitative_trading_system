export interface ShortcutConfig {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  alt?: boolean
  handler: (e?: KeyboardEvent) => void
  description?: string
}

const _shortcuts: ShortcutConfig[] = []
let _listenerActive = false
let _boundHandler: ((e: KeyboardEvent) => void) | null = null

function onGlobalKeyDown(e: KeyboardEvent): void {
  const target = e.target as HTMLElement
  const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable

  for (const s of _shortcuts) {
    if (e.key.toLowerCase() !== s.key.toLowerCase()) continue
    if (!!e.ctrlKey !== !!s.ctrl) continue
    if (!!e.metaKey !== !!s.meta) continue
    if (!!e.shiftKey !== !!s.shift) continue
    if (!!e.altKey !== !!s.alt) continue

    if (isInput && s.key !== 'Escape') continue

    e.preventDefault()
    s.handler(e)
    return
  }
}

function ensureListener(): void {
  if (_listenerActive) return
  _boundHandler = onGlobalKeyDown
  window.addEventListener('keydown', _boundHandler)
  _listenerActive = true
}

function removeListenerIfNeeded(): void {
  if (_shortcuts.length > 0 || !_listenerActive) return
  if (_boundHandler) {
    window.removeEventListener('keydown', _boundHandler)
    _boundHandler = null
  }
  _listenerActive = false
}

export function registerGlobalShortcut(config: ShortcutConfig): () => void {
  _shortcuts.push(config)
  ensureListener()

  return () => {
    const idx = _shortcuts.indexOf(config)
    if (idx >= 0) _shortcuts.splice(idx, 1)
    removeListenerIfNeeded()
  }
}

export function getRegisteredShortcuts(): ShortcutConfig[] {
  return [..._shortcuts]
}

export function _resetState(): void {
  _shortcuts.length = 0
  if (_boundHandler) {
    window.removeEventListener('keydown', _boundHandler)
    _boundHandler = null
  }
  _listenerActive = false
}

export const NAVIGATION_SHORTCUTS: ShortcutConfig[] = [
  { key: '1', alt: true, handler: () => navigateTo('/'), description: '跳转到仪表盘' },
  { key: '2', alt: true, handler: () => navigateTo('/market'), description: '跳转到行情' },
  { key: '3', alt: true, handler: () => navigateTo('/strategy'), description: '跳转到策略' },
  { key: '4', alt: true, handler: () => navigateTo('/portfolio'), description: '跳转到持仓' },
  { key: '5', alt: true, handler: () => navigateTo('/watchlist'), description: '跳转到关注' },
  { key: '/', handler: () => focusSearch(), description: '聚焦搜索框' },
  { key: 'Escape', handler: () => blurActive(), description: '取消聚焦' },
]

let _routerPush: ((path: string) => void) | null = null
let _openSearch: (() => void) | null = null

function navigateTo(path: string): void {
  if (_routerPush) _routerPush(path)
}

function focusSearch(): void {
  if (_openSearch) {
    _openSearch()
    return
  }
  const trigger = document.querySelector<HTMLButtonElement>('.search-trigger')
  if (trigger) { trigger.click(); return }
  const input = document.querySelector<HTMLInputElement>('.search-input, [data-search-input]')
  if (input) input.focus()
}

function blurActive(): void {
  const el = document.activeElement
  if (el instanceof HTMLElement && el.tagName !== 'BODY') el.blur()
}

export function registerNavigationShortcuts(
  routerPush: (path: string) => void,
  openSearch?: () => void,
): () => void {
  _routerPush = routerPush
  _openSearch = openSearch ?? null
  const unregisters = NAVIGATION_SHORTCUTS.map(s => registerGlobalShortcut(s))
  return () => {
    for (const u of unregisters) u()
    _routerPush = null
    _openSearch = null
  }
}
