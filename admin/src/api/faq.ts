import { api } from './client'

export interface FaqEntry {
  trigger: string
  response: string
}

// FAQ API
export const faqApi = {
  getAll: () =>
    api.get<{ faq: Record<string, string> }>('/admin/faq'),

  add: (trigger: string, response: string) =>
    api.post<{ status: string; trigger: string }>('/admin/faq', { trigger, response }),

  update: (oldTrigger: string, trigger: string, response: string) =>
    api.put<{ status: string; trigger: string }>(`/admin/faq/${encodeURIComponent(oldTrigger)}`, { trigger, response }),

  delete: (trigger: string) =>
    api.delete<{ status: string; deleted: string }>(`/admin/faq/${encodeURIComponent(trigger)}`),

  reload: () =>
    api.post<{ status: string; count: number }>('/admin/faq/reload'),

  test: (text: string) =>
    api.post<{ match: boolean; response: string | null }>('/admin/faq/test', { text }),
}
