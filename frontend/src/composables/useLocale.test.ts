import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { enableAutoUnmount, mount } from '@vue/test-utils'
import { defineComponent } from 'vue'
import { createI18n } from 'vue-i18n'
import zhCN from '@/i18n/locales/zh-CN'
import enUS from '@/i18n/locales/en-US'
import { useLocale } from './useLocale'

enableAutoUnmount(afterEach)

function createTestI18n(locale = 'zh-CN') {
  return createI18n({
    legacy: false,
    locale,
    fallbackLocale: 'zh-CN',
    messages: { 'zh-CN': zhCN, 'en-US': enUS },
  })
}

function mountWithI18n(locale = 'zh-CN') {
  const i18n = createTestI18n(locale)
  const wrapper = mount(
    defineComponent({
      setup() {
        const localeApi = useLocale()
        return { ...localeApi }
      },
      template: '<div />',
    }),
    { global: { plugins: [i18n] } },
  )
  return { wrapper, i18n }
}

describe('useLocale', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('returns current locale', () => {
    const { wrapper } = mountWithI18n('zh-CN')
    expect(wrapper.vm.currentLocale).toBe('zh-CN')
  })

  it('switches locale via setLocale', async () => {
    const { wrapper } = mountWithI18n('zh-CN')
    wrapper.vm.setLocale('en-US')
    await wrapper.vm.$nextTick()
    expect(wrapper.vm.currentLocale).toBe('en-US')
  })

  it('persists locale to localStorage', () => {
    const { wrapper } = mountWithI18n('zh-CN')
    wrapper.vm.setLocale('en-US')
    expect(localStorage.getItem('quantcore-locale')).toBe('en-US')
  })

  it('returns correct locale labels', () => {
    const { wrapper } = mountWithI18n('zh-CN')
    expect(wrapper.vm.localeLabel('zh-CN')).toBe('简体中文')
    expect(wrapper.vm.localeLabel('en-US')).toBe('English')
  })

  it('translates keys via t function', () => {
    const { wrapper } = mountWithI18n('zh-CN')
    expect(wrapper.vm.t('nav.dashboard')).toBe('仪表盘')
  })

  it('translates keys in English locale', () => {
    const { wrapper } = mountWithI18n('en-US')
    expect(wrapper.vm.t('nav.dashboard')).toBe('Dashboard')
  })

  it('ignores unsupported locale in setLocale', () => {
    const { wrapper } = mountWithI18n('zh-CN')
    wrapper.vm.setLocale('fr-FR' as 'zh-CN')
    expect(wrapper.vm.currentLocale).toBe('zh-CN')
  })

  it('sets document lang attribute on locale change', () => {
    const { wrapper } = mountWithI18n('zh-CN')
    wrapper.vm.setLocale('en-US')
    expect(document.documentElement.getAttribute('lang')).toBe('en-US')
  })
})
