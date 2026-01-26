import { api } from './client'

export interface WidgetConfig {
  enabled: boolean
  title: string
  greeting: string
  placeholder: string
  primary_color: string
  position: 'left' | 'right'
  allowed_domains: string[]
  tunnel_url: string
}

export const widgetApi = {
  getConfig: () =>
    api.get<{ config: WidgetConfig }>('/admin/widget/config'),

  saveConfig: (config: WidgetConfig) =>
    api.post<{ status: string; config: WidgetConfig }>('/admin/widget/config', config),
}
