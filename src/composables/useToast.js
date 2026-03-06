/**
 * Composable for displaying toast notifications.
 *
 * Wraps `useUiStore().showToast()` with convenience methods so components
 * don't need to import the UI store directly or remember type strings.
 *
 * Usage:
 *   const toast = useToast()
 *   toast.success('Saved!')
 *   toast.error('Something went wrong')
 *   toast.info('Heads up…')
 */

import { useUiStore } from '@/stores/ui'

export function useToast() {
  const ui = useUiStore()
  return {
    success: (msg, duration) => ui.showToast(msg, 'success', duration),
    error: (msg, duration) => ui.showToast(msg, 'error', duration),
    info: (msg, duration) => ui.showToast(msg, 'info', duration),
    dismiss: () => ui.dismissToast(),
  }
}
