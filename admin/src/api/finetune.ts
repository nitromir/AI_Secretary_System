import { api, createSSE } from './client'

export interface DatasetStats {
  total_sessions: number
  total_messages: number
  total_tokens: number
  avg_tokens_per_message: number
  file_path: string | null
  file_size_mb: number
  modified: string | null
}

export interface DatasetFile {
  name: string
  path: string
  size_mb: number
  modified: string
  type?: string
}

export interface TrainingConfig {
  base_model: string
  lora_rank: number
  lora_alpha: number
  lora_dropout: number
  batch_size: number
  gradient_accumulation_steps: number
  learning_rate: number
  num_epochs: number
  warmup_ratio: number
  max_seq_length: number
  output_dir: string
}

export interface TrainingStatus {
  is_running: boolean
  current_step: number
  total_steps: number
  current_epoch: number
  total_epochs: number
  loss: number
  learning_rate: number
  elapsed_seconds: number
  eta_seconds: number
  error: string | null
}

export interface Adapter {
  name: string
  path: string
  size_mb: number
  modified: string
  active: boolean
  config: Record<string, unknown> | null
}

// Finetune API
export const finetuneApi = {
  // Dataset
  uploadDataset: (file: File) =>
    api.upload<{ status: string; message: string; path: string; size_mb: number }>(
      '/admin/finetune/dataset/upload',
      file
    ),

  processDataset: () =>
    api.post<{ status: string; message: string; output_file?: string; examples_count?: number }>(
      '/admin/finetune/dataset/process'
    ),

  getDatasetStats: () =>
    api.get<{ stats: DatasetStats }>('/admin/finetune/dataset/stats'),

  listDatasets: () =>
    api.get<{ datasets: DatasetFile[] }>('/admin/finetune/dataset/list'),

  augmentDataset: () =>
    api.post<{ status: string; message: string; stats?: DatasetStats }>(
      '/admin/finetune/dataset/augment'
    ),

  // Config
  getConfig: () =>
    api.get<{
      config: TrainingConfig
      presets: Record<string, Partial<TrainingConfig>>
    }>('/admin/finetune/config'),

  setConfig: (config: Partial<TrainingConfig>) =>
    api.post<{ status: string; config?: TrainingConfig }>('/admin/finetune/config', config),

  // Training
  startTraining: () =>
    api.post<{ status: string; message: string; config?: TrainingConfig; pid?: number }>(
      '/admin/finetune/train/start'
    ),

  stopTraining: () =>
    api.post<{ status: string; message: string }>('/admin/finetune/train/stop'),

  getTrainingStatus: () =>
    api.get<{ status: TrainingStatus }>('/admin/finetune/train/status'),

  streamTrainingLog: (onMessage: (data: { type: string; line?: string; status?: TrainingStatus }) => void) =>
    createSSE<{ type: string; line?: string; status?: TrainingStatus }>('/admin/finetune/train/log', onMessage),

  // Adapters
  listAdapters: () =>
    api.get<{ adapters: Adapter[]; active: string | null }>('/admin/finetune/adapters'),

  activateAdapter: (adapter: string) =>
    api.post<{ status: string; message: string; adapter?: string; path?: string; note?: string }>(
      '/admin/finetune/adapters/activate',
      { adapter }
    ),

  deleteAdapter: (name: string) =>
    api.delete<{ status: string; message: string }>(`/admin/finetune/adapters/${name}`),
}
