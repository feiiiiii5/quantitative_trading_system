import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import ErrorBoundary from './ErrorBoundary.vue'

vi.mock('@/composables/useLogger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}))

function mountWithChild(child: ReturnType<typeof defineComponent>) {
  const Wrapper = defineComponent({
    components: { ErrorBoundary, Child: child },
    template: `<ErrorBoundary><Child /></ErrorBoundary>`,
  })
  return mount(Wrapper, {
    global: { config: { errorHandler: () => {} } },
  })
}

describe('ErrorBoundary', () => {
  it('renders slot content when no error', () => {
    const wrapper = mount(ErrorBoundary, {
      slots: { default: '<div>child content</div>' },
    })
    expect(wrapper.text()).toContain('child content')
  })

  it('shows error UI when child throws in event handler', async () => {
    const ClickThrow = defineComponent({
      name: 'ClickThrow',
      setup() {
        function boom() {
          throw new Error('click error')
        }
        return { boom }
      },
      render() {
        return h('button', { onClick: this.boom }, 'click')
      },
    })
    const wrapper = mountWithChild(ClickThrow)
    const eb = wrapper.findComponent(ErrorBoundary)
    expect(eb.find('.error-boundary').exists()).toBe(false)

    await wrapper.find('button').trigger('click')
    await nextTick()
    expect(eb.find('.error-boundary').exists()).toBe(true)
    expect(eb.text()).toContain('click error')
  })

  it('retry resets error state', async () => {
    const ClickThrow = defineComponent({
      name: 'ClickThrow',
      setup() {
        function boom() {
          throw new Error('click error')
        }
        return { boom }
      },
      render() {
        return h('button', { onClick: this.boom }, 'click')
      },
    })
    const wrapper = mountWithChild(ClickThrow)
    const eb = wrapper.findComponent(ErrorBoundary)

    await wrapper.find('button').trigger('click')
    await nextTick()
    expect(eb.find('.error-boundary').exists()).toBe(true)

    await eb.find('button').trigger('click')
    expect(eb.find('.error-boundary').exists()).toBe(false)
  })

  it('shows default message for non-Error throws', async () => {
    const ClickThrowString = defineComponent({
      name: 'ClickThrowString',
      setup() {
        function boom() {
          throw 'string error'
        }
        return { boom }
      },
      render() {
        return h('button', { onClick: this.boom }, 'click')
      },
    })
    const wrapper = mountWithChild(ClickThrowString)
    const eb = wrapper.findComponent(ErrorBoundary)

    await wrapper.find('button').trigger('click')
    await nextTick()
    expect(eb.text()).toContain('未知错误')
  })
})
