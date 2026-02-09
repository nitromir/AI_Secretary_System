import type { DemoRoute } from './types'

export const ttsFinetueRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/tts-finetune\/config$/,
    handler: () => ({
      config: {
        dataset: {
          voice_name: 'custom_voice',
          whisper_model: 'small',
          language: 'ru',
          min_duration_sec: 1.0,
          max_duration_sec: 15.0,
        },
        training: {
          base_model: 'coqui/XTTS-v2',
          batch_size: 4,
          gradient_accumulation_steps: 2,
          learning_rate: 0.00005,
          num_epochs: 10,
          output_dir: 'tts_finetune/output',
        },
      },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts-finetune\/config$/,
    handler: ({ body }) => ({ status: 'ok', config: body }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts-finetune\/samples$/,
    handler: () => ({ samples: [] }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts-finetune\/samples\/upload$/,
    handler: () => ({
      status: 'ok',
      sample: { filename: 'sample.wav', path: 'tts_finetune/samples/sample.wav', duration_sec: 5.2, transcript: '', transcript_edited: false, size_kb: 166 },
    }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/tts-finetune\/samples\//,
    handler: () => ({ status: 'ok', message: 'Sample deleted' }),
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/tts-finetune\/samples\/([^/]+)\/transcript$/,
    handler: () => ({
      status: 'ok',
      sample: { filename: 'sample.wav', path: 'tts_finetune/samples/sample.wav', duration_sec: 5.2, transcript: 'Updated text', transcript_edited: true, size_kb: 166 },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts-finetune\/transcribe$/,
    handler: () => ({ status: 'ok', message: 'Transcription started' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts-finetune\/prepare$/,
    handler: () => ({ status: 'ok', message: 'Dataset prepared' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts-finetune\/processing-status$/,
    handler: () => ({
      status: { is_running: false, stage: 'idle', current: 0, total: 0, message: '', error: null },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts-finetune\/train\/start$/,
    handler: () => ({ status: 'ok', message: 'Training started (demo)' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts-finetune\/train\/stop$/,
    handler: () => ({ status: 'ok', message: 'Training stopped' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts-finetune\/train\/status$/,
    handler: () => ({
      status: { is_running: false, current_step: 0, total_steps: 0, current_epoch: 0, total_epochs: 0, loss: 0, elapsed_seconds: 0, eta_seconds: 0, error: null },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts-finetune\/train\/log$/,
    handler: () => ({ log: [] }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts-finetune\/models$/,
    handler: () => ({ models: [] }),
  },
]
