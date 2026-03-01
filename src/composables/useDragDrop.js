/**
 * Reusable composable for HTML5 drag-and-drop state management.
 *
 * Provides reactive drag state (dragged item ID, source key, drop target)
 * and standard event handlers (start, end, dragover, dragleave) that can
 * be wired to any template with minimal boilerplate.
 *
 * Usage:
 *   const { draggedId, isDragging, startDrag, endDrag, ... } = useDragDrop()
 */
import { ref, computed } from 'vue'

export function useDragDrop() {
  /** ID of the item currently being dragged (null when idle) */
  const draggedId = ref(null)
  /** Key identifying the source zone / column the item was dragged from */
  const dragSourceKey = ref(null)
  /** Index inside the source zone (-1 for pool items) */
  const dragSourceIndex = ref(-1)
  /** Key of the drop zone currently being hovered over */
  const dragOverTarget = ref(null)

  /** Convenience flag – true while a drag is active */
  const isDragging = computed(() => draggedId.value !== null)

  /**
   * Call from a @dragstart handler.
   * Sets dataTransfer properties FIRST, then updates reactive state.
   * This ordering prevents browsers from cancelling the drag due to
   * reactive DOM updates that occur before the drag is fully initialised.
   */
  function startDrag(e, id, sourceKey, sourceIndex = -1) {
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', String(id))
    draggedId.value = id
    dragSourceKey.value = sourceKey
    dragSourceIndex.value = sourceIndex
  }

  /** Reset all drag state – call from @dragend */
  function endDrag() {
    draggedId.value = null
    dragSourceKey.value = null
    dragSourceIndex.value = -1
    dragOverTarget.value = null
  }

  /** Call from @dragover – sets dropEffect and tracks the hovered target */
  function handleDragOver(e, target) {
    e.dataTransfer.dropEffect = 'move'
    dragOverTarget.value = target
  }

  /**
   * Call from @dragleave – clears the hovered target only when the cursor
   * truly leaves the element (ignores bubbled events from children).
   */
  function handleDragLeave(e, target) {
    if (dragOverTarget.value === target) {
      const rect = e.currentTarget.getBoundingClientRect()
      const { clientX: x, clientY: y } = e
      if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
        dragOverTarget.value = null
      }
    }
  }

  return {
    draggedId,
    dragSourceKey,
    dragSourceIndex,
    dragOverTarget,
    isDragging,
    startDrag,
    endDrag,
    handleDragOver,
    handleDragLeave,
  }
}
