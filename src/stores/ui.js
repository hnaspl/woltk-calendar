import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarOpen = ref(false)
  const activeModal = ref(null)
  const toast = ref(null)
  let toastTimer = null

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function openSidebar() {
    sidebarOpen.value = true
  }

  function closeSidebar() {
    sidebarOpen.value = false
  }

  function openModal(name, data = null) {
    activeModal.value = { name, data }
  }

  function closeModal() {
    activeModal.value = null
  }

  function showToast(message, type = 'info', duration = 3500) {
    if (toastTimer) clearTimeout(toastTimer)
    toast.value = { message, type }
    toastTimer = setTimeout(() => {
      toast.value = null
    }, duration)
  }

  function dismissToast() {
    if (toastTimer) clearTimeout(toastTimer)
    toast.value = null
  }

  return {
    sidebarOpen,
    activeModal,
    toast,
    toggleSidebar,
    openSidebar,
    closeSidebar,
    openModal,
    closeModal,
    showToast,
    dismissToast
  }
})
