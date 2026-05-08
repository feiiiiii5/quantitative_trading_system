import { createI18n } from 'vue-i18n'
import zhCN from './locales/zh-CN'
import enUS from './locales/en-US'

const STORAGE_KEY = 'quantcore-locale'
const DEFAULT_LOCALE = 'zh-CN'
const SUPPORTED_LOCALES = ['zh-CN', 'en-US'] as const

export type SupportedLocale = typeof SUPPORTED_LOCALES[number]

function detectLocale(): SupportedLocale {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
    return stored as SupportedLocale
  }
  const browserLang = navigator.language
  if (browserLang.startsWith('zh')) return 'zh-CN'
  return 'en-US'
}

const i18n = createI18n({
  legacy: false,
  locale: detectLocale(),
  fallbackLocale: DEFAULT_LOCALE,
  messages: {
    'zh-CN': zhCN,
    'en-US': enUS,
  },
})

export { SUPPORTED_LOCALES, STORAGE_KEY, DEFAULT_LOCALE }
export default i18n
