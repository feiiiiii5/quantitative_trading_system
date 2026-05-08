<template>
  <div :data-theme="themeStore.theme">
    <router-view v-if="isPublicRoute" v-slot="{ Component }">
      <component :is="Component" />
    </router-view>

    <AppLayout v-else>
      <router-view v-slot="{ Component, route: currentRoute }">
        <component :is="Component" :key="currentRoute.path" />
      </router-view>
    </AppLayout>
    <KeyboardShortcutOverlay />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
import AppLayout from '@/components/layout/AppLayout.vue'
import KeyboardShortcutOverlay from '@/components/ui/KeyboardShortcutOverlay.vue'

const themeStore = useThemeStore()
const route = useRoute()
const router = useRouter()

const isPublicRoute = computed(() => {
  return route.meta?.public === true || route.path === '/' || route.path === '/login'
})

const NAV_SHORTCUTS: Record<string, string> = {
  '1': '/dashboard',
  '2': '/market',
  '3': '/strategy',
  '4': '/portfolio',
  '5': '/watchlist',
}

function onKeydown(e: KeyboardEvent) {
  if (e.metaKey || e.ctrlKey) {
    if (e.key === 'd') {
      e.preventDefault()
      themeStore.toggle()
    }
    if (NAV_SHORTCUTS[e.key]) {
      e.preventDefault()
      router.push(NAV_SHORTCUTS[e.key])
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>


