<script setup lang="ts">
import { useConfirmStore } from '@/stores/confirm'
import { computed, watch, ref } from 'vue'

const confirmStore = useConfirmStore()
const inputRef = ref<HTMLInputElement | null>(null)

// Focus input when dialog opens
watch(() => confirmStore.isOpen, (isOpen) => {
  if (isOpen && confirmStore.options?.requireInput) {
    setTimeout(() => inputRef.value?.focus(), 100)
  }
})

const typeClasses = computed(() => {
  switch (confirmStore.options?.type) {
    case 'danger':
      return {
        icon: 'bg-red-900/50 text-red-400',
        button: 'bg-red-600 hover:bg-red-500 focus:ring-red-500'
      }
    case 'warning':
      return {
        icon: 'bg-yellow-900/50 text-yellow-400',
        button: 'bg-yellow-600 hover:bg-yellow-500 focus:ring-yellow-500'
      }
    default:
      return {
        icon: 'bg-blue-900/50 text-blue-400',
        button: 'bg-blue-600 hover:bg-blue-500 focus:ring-blue-500'
      }
  }
})

const iconPath = computed(() => {
  switch (confirmStore.options?.type) {
    case 'danger':
      return 'M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z'
    case 'warning':
      return 'M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z'
    default:
      return 'M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z'
  }
})

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && confirmStore.canConfirm()) {
    confirmStore.accept()
  } else if (e.key === 'Escape') {
    confirmStore.cancel()
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="ease-out duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="confirmStore.isOpen"
        class="fixed inset-0 z-50 overflow-y-auto"
        @keydown="handleKeydown"
      >
        <div class="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
          <!-- Backdrop -->
          <div
            class="fixed inset-0 bg-black/75 transition-opacity"
            @click="confirmStore.cancel"
          />

          <!-- Dialog -->
          <Transition
            enter-active-class="ease-out duration-300"
            enter-from-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            enter-to-class="opacity-100 translate-y-0 sm:scale-100"
            leave-active-class="ease-in duration-200"
            leave-from-class="opacity-100 translate-y-0 sm:scale-100"
            leave-to-class="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
          >
            <div
              v-if="confirmStore.isOpen"
              class="relative transform overflow-hidden rounded-lg bg-zinc-900 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6"
            >
              <div class="sm:flex sm:items-start">
                <div
                  :class="[
                    'mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full sm:mx-0 sm:h-10 sm:w-10',
                    typeClasses.icon
                  ]"
                >
                  <svg
                    class="h-6 w-6"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke-width="1.5"
                    stroke="currentColor"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      :d="iconPath"
                    />
                  </svg>
                </div>
                <div class="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left flex-1">
                  <h3 class="text-base font-semibold leading-6 text-white">
                    {{ confirmStore.options?.title }}
                  </h3>
                  <div class="mt-2">
                    <p class="text-sm text-gray-400 whitespace-pre-line">
                      {{ confirmStore.options?.message }}
                    </p>
                  </div>

                  <!-- Input confirmation -->
                  <div v-if="confirmStore.options?.requireInput" class="mt-4">
                    <input
                      ref="inputRef"
                      v-model="confirmStore.inputValue"
                      type="text"
                      :placeholder="confirmStore.options?.inputPlaceholder"
                      class="block w-full rounded-md border-0 bg-zinc-800 px-3 py-2 text-white shadow-sm ring-1 ring-inset ring-zinc-700 placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-red-500 sm:text-sm sm:leading-6"
                      @keydown.enter="confirmStore.canConfirm() && confirmStore.accept()"
                    />
                  </div>
                </div>
              </div>
              <div class="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse gap-3">
                <button
                  type="button"
                  :disabled="!confirmStore.canConfirm()"
                  :class="[
                    'inline-flex w-full justify-center rounded-md px-3 py-2 text-sm font-semibold text-white shadow-sm sm:w-auto transition-colors',
                    typeClasses.button,
                    !confirmStore.canConfirm() && 'opacity-50 cursor-not-allowed'
                  ]"
                  @click="confirmStore.accept"
                >
                  {{ confirmStore.options?.confirmText }}
                </button>
                <button
                  type="button"
                  class="mt-3 inline-flex w-full justify-center rounded-md bg-zinc-800 px-3 py-2 text-sm font-semibold text-gray-300 shadow-sm ring-1 ring-inset ring-zinc-700 hover:bg-zinc-700 sm:mt-0 sm:w-auto"
                  @click="confirmStore.cancel"
                >
                  {{ confirmStore.options?.cancelText }}
                </button>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
