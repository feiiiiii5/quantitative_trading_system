import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useFocusTrap } from './useFocusTrap'

function createContainerWithButtons(): HTMLElement {
  const container = document.createElement('div')
  const btn1 = document.createElement('button')
  btn1.textContent = 'First'
  const btn2 = document.createElement('button')
  btn2.textContent = 'Second'
  const btn3 = document.createElement('button')
  btn3.textContent = 'Last'
  container.appendChild(btn1)
  container.appendChild(btn2)
  container.appendChild(btn3)
  document.body.appendChild(container)
  return container
}

describe('useFocusTrap', () => {
  let container: HTMLElement

  beforeEach(() => {
    container = createContainerWithButtons()
  })

  it('activates and sets isActive to true', () => {
    const containerRef = ref(container)
    const { activate, isActive } = useFocusTrap(containerRef)

    activate()
    expect(isActive.value).toBe(true)
  })

  it('deactivates and sets isActive to false', () => {
    const containerRef = ref(container)
    const { activate, deactivate, isActive } = useFocusTrap(containerRef)

    activate()
    deactivate()
    expect(isActive.value).toBe(false)
  })

  it('focuses first focusable element on activate', () => {
    const containerRef = ref(container)
    const { activate } = useFocusTrap(containerRef)

    activate()
    const firstBtn = container.querySelector('button')
    expect(document.activeElement).toBe(firstBtn)
  })

  it('focuses initialFocus element when specified', () => {
    container.children[1].id = 'target'
    const containerRef = ref(container)
    const { activate } = useFocusTrap(containerRef, { initialFocus: '#target' })

    activate()
    expect(document.activeElement).toBe(container.children[1])
  })

  it('deactivates on Escape when escapeDeactivates is true', () => {
    const containerRef = ref(container)
    const { activate, isActive } = useFocusTrap(containerRef, { escapeDeactivates: true })

    activate()
    expect(isActive.value).toBe(true)

    const event = new KeyboardEvent('keydown', { key: 'Escape' })
    document.dispatchEvent(event)
    expect(isActive.value).toBe(false)
  })

  it('does not deactivate on Escape when escapeDeactivates is false', () => {
    const containerRef = ref(container)
    const { activate, isActive } = useFocusTrap(containerRef, { escapeDeactivates: false })

    activate()
    const event = new KeyboardEvent('keydown', { key: 'Escape' })
    document.dispatchEvent(event)
    expect(isActive.value).toBe(true)
  })

  it('handles empty container gracefully', () => {
    const empty = document.createElement('div')
    document.body.appendChild(empty)
    const containerRef = ref(empty)
    const { activate, isActive } = useFocusTrap(containerRef)

    activate()
    expect(isActive.value).toBe(true)
  })

  it('handles null containerRef gracefully', () => {
    const containerRef = ref<HTMLElement | null>(null)
    const { activate, isActive } = useFocusTrap(containerRef)

    activate()
    expect(isActive.value).toBe(true)
  })
})
