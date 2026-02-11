import { api } from './client'

export interface WikiRagStats {
  sections_indexed: number
  files_indexed: number
  unique_tokens: number
  available: boolean
}

export interface WikiSearchResult {
  title: string
  body: string
  source_file: string
  score: number
}

export interface KnowledgeDocument {
  id: number
  filename: string
  title: string
  source_type: string
  file_size_bytes: number
  section_count: number
  owner_id: number | null
  created: string | null
  updated: string | null
}

export const wikiRagApi = {
  getStats: () =>
    api.get<{ stats: WikiRagStats; source_files: string[] }>('/admin/wiki-rag/stats'),

  reload: () =>
    api.post<{ status: string; previous_sections: number; current_sections: number; files_indexed: number }>('/admin/wiki-rag/reload'),

  search: (query: string, topK: number = 3) =>
    api.post<{ results: WikiSearchResult[]; query: string }>('/admin/wiki-rag/search', { query, top_k: topK }),

  getDocuments: () =>
    api.get<{ documents: KnowledgeDocument[]; synced: number }>('/admin/wiki-rag/documents'),

  uploadDocument: (file: File) =>
    api.upload<{ status: string; document: KnowledgeDocument }>('/admin/wiki-rag/documents/upload', file),

  getDocument: (id: number) =>
    api.get<{ document: KnowledgeDocument; content_preview: string }>(`/admin/wiki-rag/documents/${id}`),

  updateDocument: (id: number, data: { title?: string; content?: string }) =>
    api.put<{ status: string; document: KnowledgeDocument }>(`/admin/wiki-rag/documents/${id}`, data),

  deleteDocument: (id: number) =>
    api.delete<{ status: string; deleted: string }>(`/admin/wiki-rag/documents/${id}`),
}
