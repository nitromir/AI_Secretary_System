import type { DemoRoute } from './types'
import { daysAgo } from './store'

const localModels = [
  {
    name: 'Qwen2.5-7B-Instruct-AWQ',
    path: '/root/.cache/huggingface/hub/models--Qwen--Qwen2.5-7B-Instruct-AWQ',
    size_gb: 4.1,
    type: 'llm',
    format: 'AWQ',
    source: 'huggingface',
    modified: daysAgo(30),
    is_cached: true,
    repo_id: 'Qwen/Qwen2.5-7B-Instruct-AWQ',
  },
  {
    name: 'vosk-model-ru-0.42',
    path: '/root/AI_Secretary_System/models/vosk/vosk-model-ru-0.42',
    size_gb: 1.8,
    type: 'stt',
    format: 'native',
    source: 'local',
    modified: daysAgo(60),
    is_cached: false,
    repo_id: null,
  },
  {
    name: 'XTTS-v2',
    path: '/root/.cache/huggingface/hub/models--coqui--XTTS-v2',
    size_gb: 1.9,
    type: 'tts',
    format: 'pytorch',
    source: 'huggingface',
    modified: daysAgo(45),
    is_cached: true,
    repo_id: 'coqui/XTTS-v2',
  },
]

export const modelsRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/models\/list$/,
    handler: () => ({ models: localModels }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/models\/scan$/,
    handler: () => ({ status: 'ok', message: 'Scan started' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/models\/scan\/cancel$/,
    handler: () => ({ status: 'ok', message: 'Scan cancelled' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/models\/scan\/status$/,
    handler: () => ({
      status: { is_active: false, current_path: '', files_scanned: 0, models_found: 3, error: null },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/models\/download$/,
    handler: () => ({ status: 'ok', message: 'Download started (demo — no actual download)' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/models\/download\/cancel$/,
    handler: () => ({ status: 'ok', message: 'Download cancelled' }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/models\/download\/status$/,
    handler: () => ({
      status: { is_active: false, repo_id: '', filename: '', downloaded_bytes: 0, total_bytes: 0, speed_mbps: 0, eta_seconds: 0, error: null, completed: false },
    }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/models\/delete/,
    handler: () => ({ status: 'ok', message: 'Model deleted (demo)', freed_gb: 4.1 }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/models\/search/,
    handler: () => ({
      results: [
        { repo_id: 'Qwen/Qwen2.5-7B-Instruct-AWQ', author: 'Qwen', downloads: 150000, likes: 450, tags: ['text-generation', 'awq'], pipeline_tag: 'text-generation', last_modified: daysAgo(10) },
        { repo_id: 'Qwen/Qwen2.5-14B-Instruct-AWQ', author: 'Qwen', downloads: 89000, likes: 320, tags: ['text-generation', 'awq'], pipeline_tag: 'text-generation', last_modified: daysAgo(10) },
      ],
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/models\/details\//,
    handler: () => ({
      details: {
        repo_id: 'Qwen/Qwen2.5-7B-Instruct-AWQ',
        author: 'Qwen',
        downloads: 150000,
        likes: 450,
        tags: ['text-generation', 'awq', 'qwen2'],
        pipeline_tag: 'text-generation',
        library_name: 'transformers',
        total_size_gb: 4.1,
        files: [
          { name: 'model.safetensors', size_mb: 4096 },
          { name: 'config.json', size_mb: 0.01 },
          { name: 'tokenizer.json', size_mb: 7.2 },
        ],
        card_data: null,
      },
    }),
  },
]
