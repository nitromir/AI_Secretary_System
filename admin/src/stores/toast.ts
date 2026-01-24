import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  type: ToastType
  title: string
  message?: string
  duration: number
  undoAction?: () => void
  undoLabel?: string
}

let toastId = 0

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  function show(
    type: ToastType,
    title: string,
    message?: string,
    options?: {
      duration?: number
      undoAction?: () => void
      undoLabel?: string
    }
  ): number {
    const id = ++toastId
    const toast: Toast = {
      id,
      type,
      title,
      message,
      duration: options?.duration ?? (type === 'error' ? 8000 : 4000),
      undoAction: options?.undoAction,
      undoLabel: options?.undoLabel ?? 'Undo'
    }

    toasts.value.push(toast)

    // Auto-remove after duration
    if (toast.duration > 0) {
      setTimeout(() => remove(id), toast.duration)
    }

    return id
  }

  function success(title: string, message?: string, options?: { duration?: number; undoAction?: () => void }) {
    return show('success', title, message, options)
  }

  function error(title: string, message?: string, options?: { duration?: number }) {
    return show('error', title, message, { duration: options?.duration ?? 8000 })
  }

  function warning(title: string, message?: string, options?: { duration?: number }) {
    return show('warning', title, message, options)
  }

  function info(title: string, message?: string, options?: { duration?: number }) {
    return show('info', title, message, options)
  }

  function remove(id: number) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function clear() {
    toasts.value = []
  }

  function undo(id: number) {
    const toast = toasts.value.find(t => t.id === id)
    if (toast?.undoAction) {
      toast.undoAction()
      remove(id)
      success('Action undone')
    }
  }

  return {
    toasts,
    show,
    success,
    error,
    warning,
    info,
    remove,
    clear,
    undo
  }
})
