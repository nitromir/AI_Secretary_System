<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const router = useRouter()
const authStore = useAuthStore()
const toastStore = useToastStore()

const username = ref('')
const password = ref('')
const isLoading = ref(false)
const showPassword = ref(false)

async function handleSubmit() {
  if (!username.value || !password.value) {
    toastStore.warning('Please enter username and password')
    return
  }

  isLoading.value = true

  try {
    const success = await authStore.login(username.value, password.value)

    if (success) {
      toastStore.success('Welcome!', `Logged in as ${username.value}`)
      router.push('/')
    } else {
      toastStore.error('Login failed', authStore.error || 'Invalid credentials')
    }
  } catch (e) {
    toastStore.error('Login failed', 'Connection error')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-zinc-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <!-- Logo -->
      <div class="flex justify-center">
        <div class="w-16 h-16 bg-indigo-600 rounded-2xl flex items-center justify-center">
          <svg
            class="w-10 h-10 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke-width="1.5"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
            />
          </svg>
        </div>
      </div>

      <h2 class="mt-6 text-center text-3xl font-bold tracking-tight text-white">
        AI Secretary Admin
      </h2>
      <p class="mt-2 text-center text-sm text-gray-400">
        Sign in to access the admin panel
      </p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-zinc-900 py-8 px-4 shadow-xl ring-1 ring-zinc-800 sm:rounded-xl sm:px-10">
        <form class="space-y-6" @submit.prevent="handleSubmit">
          <!-- Username -->
          <div>
            <label for="username" class="block text-sm font-medium text-gray-300">
              Username
            </label>
            <div class="mt-2">
              <input
                id="username"
                v-model="username"
                name="username"
                type="text"
                autocomplete="username"
                required
                class="block w-full rounded-lg border-0 bg-zinc-800 px-3 py-2 text-white shadow-sm ring-1 ring-inset ring-zinc-700 placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6"
                placeholder="admin"
              />
            </div>
          </div>

          <!-- Password -->
          <div>
            <label for="password" class="block text-sm font-medium text-gray-300">
              Password
            </label>
            <div class="mt-2 relative">
              <input
                id="password"
                v-model="password"
                name="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                required
                class="block w-full rounded-lg border-0 bg-zinc-800 px-3 py-2 pr-10 text-white shadow-sm ring-1 ring-inset ring-zinc-700 placeholder:text-gray-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm sm:leading-6"
                placeholder="••••••••"
              />
              <button
                type="button"
                class="absolute inset-y-0 right-0 flex items-center pr-3"
                @click="showPassword = !showPassword"
              >
                <svg
                  v-if="showPassword"
                  class="h-5 w-5 text-gray-400 hover:text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
                  />
                </svg>
                <svg
                  v-else
                  class="h-5 w-5 text-gray-400 hover:text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke-width="1.5"
                  stroke="currentColor"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- Error message -->
          <div v-if="authStore.error" class="rounded-lg bg-red-900/50 p-3">
            <p class="text-sm text-red-400">{{ authStore.error }}</p>
          </div>

          <!-- Submit -->
          <div>
            <button
              type="submit"
              :disabled="isLoading"
              class="flex w-full justify-center rounded-lg bg-indigo-600 px-3 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <svg
                v-if="isLoading"
                class="animate-spin -ml-1 mr-2 h-5 w-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                />
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                />
              </svg>
              {{ isLoading ? 'Signing in...' : 'Sign in' }}
            </button>
          </div>
        </form>

        <!-- Hint -->
        <div class="mt-6 text-center space-y-1">
          <p class="text-xs text-gray-500">
            Default credentials: admin / admin
          </p>
          <p class="text-xs text-yellow-500/70">
            Dev mode: Works without backend running
          </p>
        </div>
      </div>
    </div>
  </div>
</template>
