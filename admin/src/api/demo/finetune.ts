import type { DemoRoute } from './types'
import { daysAgo } from './store'

export const finetuneRoutes: DemoRoute[] = [
  // Dataset
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/dataset\/upload$/,
    handler: () => ({ status: 'ok', message: 'File uploaded', path: 'finetune/datasets/upload.jsonl', size_mb: 2.3 }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/dataset\/process$/,
    handler: () => ({
      status: 'ok',
      message: 'Dataset processed',
      output_file: 'finetune/datasets/processed.jsonl',
      stats: { total_dialogs: 156, total_messages: 892, filtered_out: 12 },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/finetune\/dataset\/config$/,
    handler: () => ({
      config: {
        owner_name: 'AI-Секретарь',
        transcribe_voice: false,
        min_dialog_messages: 3,
        max_message_length: 2048,
        max_dialog_length: 8192,
        include_groups: false,
        output_name: 'secretary_dataset',
      },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/dataset\/config$/,
    handler: ({ body }) => ({ status: 'ok', config: body }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/finetune\/dataset\/processing-status$/,
    handler: () => ({
      status: { is_running: false, stage: 'idle', current: 0, total: 0, voice_transcribed: 0, voice_total: 0, error: null },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/finetune\/dataset\/stats$/,
    handler: () => ({
      stats: {
        total_sessions: 156,
        total_messages: 892,
        total_tokens: 45230,
        avg_tokens_per_message: 50.7,
        file_path: 'finetune/datasets/secretary_dataset.jsonl',
        file_size_mb: 2.3,
        modified: daysAgo(5),
      },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/finetune\/dataset\/list$/,
    handler: () => ({
      datasets: [
        { name: 'secretary_dataset.jsonl', path: 'finetune/datasets/secretary_dataset.jsonl', size_mb: 2.3, modified: daysAgo(5), type: 'processed' },
        { name: 'project_dataset.jsonl', path: 'finetune/datasets/project_dataset.jsonl', size_mb: 1.1, modified: daysAgo(3), type: 'generated' },
      ],
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/dataset\/augment$/,
    handler: () => ({ status: 'ok', message: 'Dataset augmented' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/dataset\/generate-project$/,
    handler: () => ({
      status: 'ok',
      message: 'Project dataset generated',
      output_file: 'finetune/datasets/project_dataset.jsonl',
      stats: { total_dialogs: 89, total_messages: 445, sources: { tz: 34, faq: 24, docs: 21, escalation: 10 } },
    }),
  },
  // Config
  {
    method: 'GET',
    pattern: /^\/admin\/finetune\/config$/,
    handler: () => ({
      config: {
        base_model: 'Qwen/Qwen2.5-7B-Instruct-AWQ',
        lora_rank: 16,
        lora_alpha: 32,
        lora_dropout: 0.05,
        batch_size: 4,
        gradient_accumulation_steps: 4,
        learning_rate: 0.0002,
        num_epochs: 3,
        warmup_ratio: 0.03,
        max_seq_length: 2048,
        output_dir: 'finetune/output',
      },
      presets: {
        'quick': { num_epochs: 1, lora_rank: 8, batch_size: 8 },
        'balanced': { num_epochs: 3, lora_rank: 16, batch_size: 4 },
        'quality': { num_epochs: 5, lora_rank: 32, batch_size: 2 },
      },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/config$/,
    handler: ({ body }) => ({ status: 'ok', config: body }),
  },
  // Training
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/train\/start$/,
    handler: () => ({ status: 'ok', message: 'Training started (demo)' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/train\/stop$/,
    handler: () => ({ status: 'ok', message: 'Training stopped' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/finetune\/train\/status$/,
    handler: () => ({
      status: { is_running: false, current_step: 0, total_steps: 0, current_epoch: 0, total_epochs: 0, loss: 0, learning_rate: 0, elapsed_seconds: 0, eta_seconds: 0, error: null },
    }),
  },
  // Adapters
  {
    method: 'GET',
    pattern: /^\/admin\/finetune\/adapters$/,
    handler: () => ({
      adapters: [
        { name: 'secretary-v1', path: 'finetune/output/secretary-v1', size_mb: 48, modified: daysAgo(7), active: true, config: { lora_rank: 16, base_model: 'Qwen2.5-7B-AWQ' } },
      ],
      active: 'secretary-v1',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/finetune\/adapters\/activate$/,
    handler: ({ body }) => ({
      status: 'ok',
      message: 'Adapter activated',
      adapter: (body as { adapter: string }).adapter,
    }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/finetune\/adapters\//,
    handler: () => ({ status: 'ok', message: 'Adapter deleted' }),
  },
]
