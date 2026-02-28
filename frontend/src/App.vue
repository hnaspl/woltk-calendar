<template>
  <RouterView />
</template>

<script setup>
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(async () => {
  // Attempt to restore session on app load
  try {
    await authStore.fetchMe()
  } catch {
    // Not authenticated – router guard will redirect
  }
})
</script>
