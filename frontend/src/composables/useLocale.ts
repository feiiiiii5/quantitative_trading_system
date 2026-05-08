import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { SUPPORTED_LOCALES, STORAGE_KEY } from '@/i18n'
import type { SupportedLocale } from '@/i18n'

export interface UseLocaleReturn {
  locale: ComputedRef<string> & { value: string }
  t: (key: string, ...args: unknown[]) => string
  currentLocale: ComputedRef<SupportedLocale>
  supportedLocales: readonly SupportedLocale[]
  setLocale: (locale: SupportedLocale) => void
  localeLabel: (locale: SupportedLocale) => string
}

import type { ComputedRef } from 'vue'

export function useLocale(): UseLocaleReturn {
  const { locale, t } = useI18n()

  const currentLocale = computed<SupportedLocale>(
    () => locale.value as SupportedLocale,
  )

  const supportedLocales = SUPPORTED_LOCALES

  function setLocale(newLocale: SupportedLocale): void {
    if (!SUPPORTED_LOCALES.includes(newLocale)) return
    locale.value = newLocale
    localStorage.setItem(STORAGE_KEY, newLocale)
    document.documentElement.setAttribute('lang', newLocale)
  }

  function localeLabel(loc: SupportedLocale): string {
    const labels: Record<SupportedLocale, string> = {
      'zh-CN': '简体中文',
      'en-US': 'English',
    }
    return labels[loc]
  }

  return { locale, t, currentLocale, supportedLocales, setLocale, localeLabel }
}
