<template>
  <AppLayout>
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </AppLayout>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
import AppLayout from '@/components/layout/AppLayout.vue'

const router = useRouter()
const themeStore = useThemeStore()

function handleGlobalKeydown(e: KeyboardEvent) {
  if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
  if (e.altKey || e.ctrlKey || e.metaKey) {
    switch (e.key) {
      case '1': e.preventDefault(); router.push('/dashboard'); break
      case '2': e.preventDefault(); router.push('/market'); break
      case '3': e.preventDefault(); router.push('/strategy'); break
      case '4': e.preventDefault(); router.push('/portfolio'); break
      case '5': e.preventDefault(); router.push('/watchlist'); break
      case 'd': e.preventDefault(); themeStore.toggleTheme(); break
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleGlobalKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})
</script>
