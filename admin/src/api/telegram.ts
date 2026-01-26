import { api } from './client'

export interface TelegramConfig {
  enabled: boolean
  bot_token: string
  bot_token_masked?: string
  api_url: string
  allowed_users: number[]
  admin_users: number[]
  welcome_message: string
  unauthorized_message: string
  error_message: string
  typing_enabled: boolean
}

export interface TelegramStatus {
  running: boolean
  enabled: boolean
  has_token: boolean
  active_sessions: number
  allowed_users_count: number
  admin_users_count: number
  pid: number | null
}

export const telegramApi = {
  getConfig: () =>
    api.get<{ config: TelegramConfig }>('/admin/telegram/config'),

  saveConfig: (config: Partial<TelegramConfig>) =>
    api.post<{ status: string; config: TelegramConfig }>('/admin/telegram/config', config),

  getStatus: () =>
    api.get<{ status: TelegramStatus }>('/admin/telegram/status'),

  start: () =>
    api.post<{ status: string; pid?: number }>('/admin/telegram/start'),

  stop: () =>
    api.post<{ status: string }>('/admin/telegram/stop'),

  restart: () =>
    api.post<{ status: string; pid?: number }>('/admin/telegram/restart'),

  getSessions: () =>
    api.get<{ sessions: Record<string, string> }>('/admin/telegram/sessions'),

  clearSessions: () =>
    api.delete<{ status: string; message: string }>('/admin/telegram/sessions'),
}
