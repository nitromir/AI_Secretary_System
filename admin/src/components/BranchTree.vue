<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { GitBranch } from 'lucide-vue-next'
import type { BranchNode } from '@/api/chat'
import BranchTreeNode from '@/components/BranchTreeNode.vue'

const props = defineProps<{
  branches: BranchNode[]
  sessionId: string
}>()

const emit = defineEmits<{
  switch: [messageId: string]
}>()

const { t } = useI18n()

const hasBranching = computed(() => {
  function check(nodes: BranchNode[]): boolean {
    if (nodes.length > 1) return true
    for (const node of nodes) {
      if (check(node.children)) return true
    }
    return false
  }
  return check(props.branches)
})

function handleClick(messageId: string) {
  emit('switch', messageId)
}
</script>

<template>
  <div
    v-if="hasBranching"
    class="w-52 border-l border-border bg-card/50 overflow-y-auto flex-shrink-0"
  >
    <div class="p-3 border-b border-border">
      <h3 class="text-xs font-semibold text-muted-foreground uppercase flex items-center gap-1.5">
        <GitBranch class="w-3.5 h-3.5" />
        {{ t('chatView.branchTree') }}
      </h3>
    </div>

    <div class="p-2">
      <BranchTreeNode
        v-for="root in branches"
        :key="root.id"
        :node="root"
        :depth="0"
        @click-node="handleClick"
      />
    </div>
  </div>
</template>
