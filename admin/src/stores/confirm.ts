import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ConfirmOptions {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  type?: 'danger' | 'warning' | 'info'
  inputPlaceholder?: string
  requireInput?: string // If set, user must type this to confirm
}

export const useConfirmStore = defineStore('confirm', () => {
  const isOpen = ref(false)
  const options = ref<ConfirmOptions | null>(null)
  const inputValue = ref('')

  let resolvePromise: ((value: boolean) => void) | null = null

  function confirm(opts: ConfirmOptions): Promise<boolean> {
    options.value = {
      confirmText: 'Confirm',
      cancelText: 'Cancel',
      type: 'warning',
      ...opts
    }
    inputValue.value = ''
    isOpen.value = true

    return new Promise((resolve) => {
      resolvePromise = resolve
    })
  }

  function confirmDelete(itemName: string, itemType: string = 'item'): Promise<boolean> {
    return confirm({
      title: `Delete ${itemType}?`,
      message: `Are you sure you want to delete "${itemName}"? This action cannot be undone.`,
      confirmText: 'Delete',
      cancelText: 'Cancel',
      type: 'danger'
    })
  }

  function confirmDangerousAction(
    title: string,
    message: string,
    confirmPhrase: string
  ): Promise<boolean> {
    return confirm({
      title,
      message: `${message}\n\nType "${confirmPhrase}" to confirm.`,
      confirmText: 'Confirm',
      cancelText: 'Cancel',
      type: 'danger',
      requireInput: confirmPhrase,
      inputPlaceholder: `Type "${confirmPhrase}" to confirm`
    })
  }

  function accept() {
    // Check if input confirmation is required
    if (options.value?.requireInput) {
      if (inputValue.value !== options.value.requireInput) {
        return // Don't close, input doesn't match
      }
    }

    isOpen.value = false
    if (resolvePromise) {
      resolvePromise(true)
      resolvePromise = null
    }
  }

  function cancel() {
    isOpen.value = false
    if (resolvePromise) {
      resolvePromise(false)
      resolvePromise = null
    }
  }

  const canConfirm = () => {
    if (!options.value?.requireInput) return true
    return inputValue.value === options.value.requireInput
  }

  return {
    isOpen,
    options,
    inputValue,
    confirm,
    confirmDelete,
    confirmDangerousAction,
    accept,
    cancel,
    canConfirm
  }
})
