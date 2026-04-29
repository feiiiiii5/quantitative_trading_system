import { ref, watch } from 'vue'

type Theme = 'dark' | 'light'

const currentTheme = ref<Theme>((localStorage.getItem('theme') as Theme) || 'dark')

function applyTheme(theme: Theme) {
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('theme', theme)
  currentTheme.value = theme
}

export function useTheme() {
  function toggleTheme() {
    applyTheme(currentTheme.value === 'dark' ? 'light' : 'dark')
  }

  function setTheme(theme: Theme) {
    applyTheme(theme)
  }

  watch(currentTheme, (theme) => {
    applyTheme(theme)
  }, { immediate: true })

  return { currentTheme, toggleTheme, setTheme }
}
