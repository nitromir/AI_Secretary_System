<script setup lang="ts">
import { useQuery, useMutation, useQueryClient } from '@tanstack/vue-query'
import { faqApi } from '@/api'
import {
  MessageSquare,
  Plus,
  Pencil,
  Trash2,
  RotateCw,
  Search,
  TestTube2,
  X,
  Info
} from 'lucide-vue-next'
import { ref, computed } from 'vue'

const queryClient = useQueryClient()

// State
const searchQuery = ref('')
const showAddModal = ref(false)
const editingEntry = ref<{ trigger: string; response: string } | null>(null)
const testText = ref('')
const testResult = ref<{ match: boolean; response: string | null } | null>(null)

const formTrigger = ref('')
const formResponse = ref('')

// Queries
const { data: faqData, isLoading, refetch } = useQuery({
  queryKey: ['faq'],
  queryFn: () => faqApi.getAll(),
})

// Mutations
const addMutation = useMutation({
  mutationFn: ({ trigger, response }: { trigger: string; response: string }) =>
    faqApi.add(trigger, response),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['faq'] })
    closeModal()
  },
})

const updateMutation = useMutation({
  mutationFn: ({ oldTrigger, trigger, response }: { oldTrigger: string; trigger: string; response: string }) =>
    faqApi.update(oldTrigger, trigger, response),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['faq'] })
    closeModal()
  },
})

const deleteMutation = useMutation({
  mutationFn: (trigger: string) => faqApi.delete(trigger),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['faq'] }),
})

const reloadMutation = useMutation({
  mutationFn: () => faqApi.reload(),
  onSuccess: () => queryClient.invalidateQueries({ queryKey: ['faq'] }),
})

const testMutation = useMutation({
  mutationFn: (text: string) => faqApi.test(text),
  onSuccess: (data) => {
    testResult.value = data
  },
})

// Computed
const faqEntries = computed(() => {
  if (!faqData.value?.faq) return []

  let entries = Object.entries(faqData.value.faq).map(([trigger, response]) => ({
    trigger,
    response,
  }))

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    entries = entries.filter(
      e => e.trigger.toLowerCase().includes(query) ||
           e.response.toLowerCase().includes(query)
    )
  }

  return entries.sort((a, b) => a.trigger.localeCompare(b.trigger))
})

// Methods
function openAddModal() {
  editingEntry.value = null
  formTrigger.value = ''
  formResponse.value = ''
  showAddModal.value = true
}

function openEditModal(entry: { trigger: string; response: string }) {
  editingEntry.value = entry
  formTrigger.value = entry.trigger
  formResponse.value = entry.response
  showAddModal.value = true
}

function closeModal() {
  showAddModal.value = false
  editingEntry.value = null
  formTrigger.value = ''
  formResponse.value = ''
}

function saveEntry() {
  if (!formTrigger.value || !formResponse.value) return

  if (editingEntry.value) {
    updateMutation.mutate({
      oldTrigger: editingEntry.value.trigger,
      trigger: formTrigger.value,
      response: formResponse.value,
    })
  } else {
    addMutation.mutate({
      trigger: formTrigger.value,
      response: formResponse.value,
    })
  }
}

function runTest() {
  if (testText.value) {
    testMutation.mutate(testText.value)
  }
}
</script>

<template>
  <div class="space-y-6">
    <!-- Toolbar -->
    <div class="flex items-center gap-4 flex-wrap">
      <button
        @click="openAddModal"
        class="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
      >
        <Plus class="w-4 h-4" />
        Add Entry
      </button>
      <button
        @click="reloadMutation.mutate()"
        :disabled="reloadMutation.isPending.value"
        class="flex items-center gap-2 px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 disabled:opacity-50 transition-colors"
      >
        <RotateCw class="w-4 h-4" />
        Reload
      </button>

      <div class="flex-1" />

      <div class="relative">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search..."
          class="pl-10 pr-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary w-64"
        />
      </div>
    </div>

    <!-- Template Variables Info -->
    <div class="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
      <div class="flex items-start gap-3">
        <Info class="w-5 h-5 text-blue-500 mt-0.5" />
        <div>
          <h3 class="font-medium text-blue-500">Template Variables</h3>
          <p class="text-sm text-muted-foreground mt-1">
            You can use these placeholders in responses:
            <code class="bg-secondary px-1 rounded">{'{'}current_time{'}'}</code>,
            <code class="bg-secondary px-1 rounded">{'{'}current_date{'}'}</code>,
            <code class="bg-secondary px-1 rounded">{'{'}day_of_week{'}'}</code>
          </p>
        </div>
      </div>
    </div>

    <!-- FAQ Test -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <TestTube2 class="w-5 h-5" />
          Test FAQ Matching
        </h2>
      </div>
      <div class="p-4">
        <div class="flex gap-2">
          <input
            v-model="testText"
            type="text"
            placeholder="Enter text to test..."
            class="flex-1 px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            @keyup.enter="runTest"
          />
          <button
            @click="runTest"
            :disabled="testMutation.isPending.value || !testText"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            Test
          </button>
        </div>

        <div v-if="testResult" class="mt-4 p-4 rounded-lg" :class="testResult.match ? 'bg-green-500/10' : 'bg-red-500/10'">
          <p v-if="testResult.match" class="text-green-500 font-medium">Match found!</p>
          <p v-else class="text-red-500 font-medium">No match - will go to LLM</p>
          <p v-if="testResult.response" class="mt-2 text-sm">
            Response: <span class="text-muted-foreground">{{ testResult.response }}</span>
          </p>
        </div>
      </div>
    </div>

    <!-- FAQ Table -->
    <div class="bg-card rounded-lg border border-border">
      <div class="p-4 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <MessageSquare class="w-5 h-5" />
          FAQ Entries
          <span class="text-sm font-normal text-muted-foreground">({{ faqEntries.length }})</span>
        </h2>
      </div>

      <div v-if="isLoading" class="p-8 text-center text-muted-foreground">
        Loading...
      </div>

      <div v-else-if="faqEntries.length === 0" class="p-8 text-center text-muted-foreground">
        {{ searchQuery ? 'No matching entries' : 'No FAQ entries yet' }}
      </div>

      <div v-else class="divide-y divide-border">
        <div
          v-for="entry in faqEntries"
          :key="entry.trigger"
          class="p-4 hover:bg-secondary/50 transition-colors"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex-1 min-w-0">
              <div class="font-medium text-primary">{{ entry.trigger }}</div>
              <div class="text-sm text-muted-foreground mt-1 line-clamp-2">
                {{ entry.response }}
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <button
                @click="openEditModal(entry)"
                class="p-2 rounded-lg bg-secondary hover:bg-secondary/80 transition-colors"
                title="Edit"
              >
                <Pencil class="w-4 h-4" />
              </button>
              <button
                @click="deleteMutation.mutate(entry.trigger)"
                :disabled="deleteMutation.isPending.value"
                class="p-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                title="Delete"
              >
                <Trash2 class="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <div
      v-if="showAddModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      @click.self="closeModal"
    >
      <div class="bg-card border border-border rounded-lg w-full max-w-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-semibold">
            {{ editingEntry ? 'Edit FAQ Entry' : 'Add FAQ Entry' }}
          </h3>
          <button
            @click="closeModal"
            class="p-1 rounded hover:bg-secondary transition-colors"
          >
            <X class="w-5 h-5" />
          </button>
        </div>

        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">Trigger (question/phrase)</label>
            <input
              v-model="formTrigger"
              type="text"
              placeholder="e.g., привет"
              class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
            />
            <p class="text-xs text-muted-foreground mt-1">Case-insensitive, partial matching</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Response</label>
            <textarea
              v-model="formResponse"
              rows="4"
              placeholder="e.g., Здравствуйте! Чем могу помочь?"
              class="w-full px-4 py-2 bg-secondary rounded-lg focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>
        </div>

        <div class="flex justify-end gap-2 mt-6">
          <button
            @click="closeModal"
            class="px-4 py-2 bg-secondary rounded-lg hover:bg-secondary/80 transition-colors"
          >
            Cancel
          </button>
          <button
            @click="saveEntry"
            :disabled="!formTrigger || !formResponse || addMutation.isPending.value || updateMutation.isPending.value"
            class="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {{ editingEntry ? 'Update' : 'Add' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
