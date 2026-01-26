import { api } from './client'

export interface ModelInfo {
  name: string
  path: string
  size_gb: number
  type: string  // "llm", "tts", "stt", "embedding", "unknown"
  format: string
  source: string  // "huggingface", "local", "ollama", "project"
  modified: string
  is_cached: boolean
  repo_id: string | null
}

export interface DownloadProgress {
  is_active: boolean
  repo_id: string
  filename: string
  downloaded_bytes: number
  total_bytes: number
  speed_mbps: number
  eta_seconds: number
  error: string | null
  completed: boolean
}

export interface ScanProgress {
  is_active: boolean
  current_path: string
  files_scanned: number
  models_found: number
  error: string | null
}

export interface HuggingFaceModel {
  repo_id: string
  author: string
  downloads: number
  likes: number
  tags: string[]
  pipeline_tag: string | null
  last_modified: string | null
}

export interface ModelDetails {
  repo_id: string
  author: string
  downloads: number
  likes: number
  tags: string[]
  pipeline_tag: string | null
  library_name: string | null
  total_size_gb: number
  files: { name: string; size_mb: number }[]
  card_data: Record<string, unknown> | null
}

// Model Management API
export const modelsApi = {
  // Local models
  listModels: () =>
    api.get<{ models: ModelInfo[] }>('/admin/models/list'),

  scanModels: (includeSystem: boolean = false) =>
    api.post<{ status: string; message: string }>('/admin/models/scan', { include_system: includeSystem }),

  cancelScan: () =>
    api.post<{ status: string; message: string }>('/admin/models/scan/cancel'),

  getScanStatus: () =>
    api.get<{ status: ScanProgress }>('/admin/models/scan/status'),

  // Download
  downloadModel: (repoId: string, revision: string = 'main') =>
    api.post<{ status: string; message: string }>('/admin/models/download', { repo_id: repoId, revision }),

  cancelDownload: () =>
    api.post<{ status: string; message: string }>('/admin/models/download/cancel'),

  getDownloadStatus: () =>
    api.get<{ status: DownloadProgress }>('/admin/models/download/status'),

  // Delete
  deleteModel: (path: string) =>
    api.delete<{ status: string; message: string; freed_gb?: number }>(`/admin/models/delete?path=${encodeURIComponent(path)}`),

  // HuggingFace search
  searchHuggingFace: (query: string, limit: number = 20) =>
    api.get<{ results: HuggingFaceModel[] }>(`/admin/models/search?query=${encodeURIComponent(query)}&limit=${limit}`),

  getModelDetails: (repoId: string) =>
    api.get<{ details: ModelDetails }>(`/admin/models/details/${encodeURIComponent(repoId)}`),
}
