<script setup lang="ts">
import { ref, onErrorCaptured } from 'vue'
import { useToastStore } from '@/stores/toast'

const hasError = ref(false)
const errorMessage = ref('')
const errorStack = ref('')
const toastStore = useToastStore()

onErrorCaptured((err, instance, info) => {
  console.error('Error captured:', err, info)

  hasError.value = true
  errorMessage.value = err instanceof Error ? err.message : String(err)
  errorStack.value = err instanceof Error ? err.stack || '' : ''

  toastStore.error('An error occurred', errorMessage.value)

  // Return false to stop the error from propagating
  return false
})

function reset() {
  hasError.value = false
  errorMessage.value = ''
  errorStack.value = ''
}

function reload() {
  window.location.reload()
}
</script>

<template>
  <div v-if="hasError" class="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
    <div class="max-w-lg w-full bg-zinc-900 rounded-xl p-6 shadow-xl ring-1 ring-zinc-800">
      <div class="flex items-center justify-center w-12 h-12 mx-auto bg-red-900/50 rounded-full">
        <svg
          class="w-6 h-6 text-red-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke-width="1.5"
          stroke="currentColor"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
          />
        </svg>
      </div>

      <h2 class="mt-4 text-xl font-semibold text-white text-center">
        Something went wrong
      </h2>

      <p class="mt-2 text-sm text-gray-400 text-center">
        An unexpected error occurred. You can try to recover or reload the page.
      </p>

      <div class="mt-4 p-3 bg-zinc-800 rounded-lg">
        <p class="text-sm text-red-400 font-mono break-all">
          {{ errorMessage }}
        </p>
      </div>

      <details v-if="errorStack" class="mt-4">
        <summary class="text-sm text-gray-500 cursor-pointer hover:text-gray-400">
          Show details
        </summary>
        <pre class="mt-2 p-3 bg-zinc-800 rounded-lg text-xs text-gray-400 overflow-x-auto">{{ errorStack }}</pre>
      </details>

      <div class="mt-6 flex gap-3">
        <button
          type="button"
          class="flex-1 px-4 py-2 bg-zinc-800 text-gray-300 rounded-lg hover:bg-zinc-700 transition-colors"
          @click="reset"
        >
          Try Again
        </button>
        <button
          type="button"
          class="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors"
          @click="reload"
        >
          Reload Page
        </button>
      </div>
    </div>
  </div>

  <slot v-else />
</template>
