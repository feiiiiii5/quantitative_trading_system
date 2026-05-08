declare module 'vue-i18n' {
  import type { ComputedRef, App } from 'vue'

  interface I18nOptions {
    legacy?: boolean
    locale?: string
    fallbackLocale?: string
    messages?: Record<string, Record<string, unknown>>
  }

  interface Composer {
    locale: ComputedRef<string> & { value: string }
    t(key: string, ...args: unknown[]): string
  }

  interface I18nInstance {
    global: Composer
    install(app: App): void
  }

  export function createI18n(options: I18nOptions): I18nInstance
  export function useI18n(): Composer
}
