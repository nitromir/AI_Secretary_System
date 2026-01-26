import { api } from './client'

export interface VoiceSample {
  filename: string
  path: string
  duration_sec: number
  transcript: string
  transcript_edited: boolean
  size_kb: number
}

export interface TTSDatasetConfig {
  voice_name: string
  whisper_model: string
  language: string
  min_duration_sec: number
  max_duration_sec: number
}

export interface TTSTrainingConfig {
  base_model: string
  batch_size: number
  gradient_accumulation_steps: number
  learning_rate: number
  num_epochs: number
  output_dir: string
}

export interface TTSConfig {
  dataset: TTSDatasetConfig
  training: TTSTrainingConfig
}

export interface TTSProcessingStatus {
  is_running: boolean
  stage: string
  current: number
  total: number
  message: string
  error: string | null
}

export interface TTSTrainingStatus {
  is_running: boolean
  current_step: number
  total_steps: number
  current_epoch: number
  total_epochs: number
  loss: number
  elapsed_seconds: number
  eta_seconds: number
  error: string | null
}

export interface TTSTrainedModel {
  name: string
  path: string
  epochs: number
  modified: string
}

// TTS Finetune API
export const ttsFinetune = {
  // Config
  getConfig: () =>
    api.get<{ config: TTSConfig }>('/admin/tts-finetune/config'),

  setConfig: (config: Partial<TTSConfig>) =>
    api.post<{ status: string; config: TTSConfig }>('/admin/tts-finetune/config', config),

  // Samples
  getSamples: () =>
    api.get<{ samples: VoiceSample[] }>('/admin/tts-finetune/samples'),

  uploadSample: (file: File) =>
    api.upload<{ status: string; sample: VoiceSample }>('/admin/tts-finetune/samples/upload', file),

  deleteSample: (filename: string) =>
    api.delete<{ status: string; message: string }>(`/admin/tts-finetune/samples/${encodeURIComponent(filename)}`),

  updateTranscript: (filename: string, transcript: string) =>
    api.put<{ status: string; sample: VoiceSample }>(
      `/admin/tts-finetune/samples/${encodeURIComponent(filename)}/transcript`,
      { transcript }
    ),

  // Processing
  transcribe: () =>
    api.post<{ status: string; message: string }>('/admin/tts-finetune/transcribe'),

  prepareDataset: () =>
    api.post<{ status: string; message: string }>('/admin/tts-finetune/prepare'),

  getProcessingStatus: () =>
    api.get<{ status: TTSProcessingStatus }>('/admin/tts-finetune/processing-status'),

  // Training
  startTraining: () =>
    api.post<{ status: string; message: string }>('/admin/tts-finetune/train/start'),

  stopTraining: () =>
    api.post<{ status: string; message: string }>('/admin/tts-finetune/train/stop'),

  getTrainingStatus: () =>
    api.get<{ status: TTSTrainingStatus }>('/admin/tts-finetune/train/status'),

  getTrainingLog: () =>
    api.get<{ log: string[] }>('/admin/tts-finetune/train/log'),

  // Models
  getTrainedModels: () =>
    api.get<{ models: TTSTrainedModel[] }>('/admin/tts-finetune/models'),
}
