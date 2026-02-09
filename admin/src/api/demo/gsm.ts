import type { DemoRoute } from './types'

export const gsmRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/gsm\/status$/,
    handler: () => ({
      state: 'disconnected',
      signal_strength: null,
      signal_percent: null,
      sim_status: null,
      network_name: null,
      network_registered: false,
      phone_number: null,
      at_port: '/dev/ttyUSB2',
      audio_port: '/dev/ttyUSB4',
      module_info: null,
      last_error: 'GSM module not connected (demo mode)',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/gsm\/initialize$/,
    handler: () => ({
      status: 'error',
      message: 'GSM module not available in demo mode',
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/gsm\/config$/,
    handler: () => ({
      at_port: '/dev/ttyUSB2',
      audio_port: '/dev/ttyUSB4',
      baud_rate: 115200,
      auto_answer: true,
      auto_answer_rings: 2,
      allowed_numbers: [],
      blocked_numbers: [],
      greeting_message: 'Здравствуйте! Вы позвонили в компанию. Чем могу помочь?',
      goodbye_message: 'Спасибо за звонок! До свидания.',
      busy_message: 'Извините, все операторы заняты. Перезвоните позже.',
      silence_timeout: 10,
      max_call_duration: 300,
      sms_enabled: true,
      sms_notify_number: '+79991234567',
      sms_missed_call_template: 'Пропущенный звонок от {number} в {time}',
      sms_voicemail_template: 'Голосовое сообщение от {number}: {text}',
      llm_backend: 'vllm',
      llm_persona: 'anna',
      tts_voice: 'anna',
      tts_preset: 'natural',
    }),
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/gsm\/config$/,
    handler: ({ body }) => body,
  },
  {
    method: 'GET',
    pattern: /^\/admin\/gsm\/calls$/,
    handler: () => ({
      calls: [],
      total: 0,
      limit: 50,
      offset: 0,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/gsm\/calls\/active$/,
    handler: () => null,
  },
  {
    method: 'POST',
    pattern: /^\/admin\/gsm\/calls\/(answer|hangup)$/,
    handler: () => ({
      status: 'error',
      message: 'No active call',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/gsm\/calls\/dial/,
    handler: () => ({
      status: 'error',
      message: 'GSM module not connected',
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/gsm\/sms$/,
    handler: () => ({
      messages: [],
      total: 0,
      limit: 50,
      offset: 0,
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/gsm\/sms$/,
    handler: () => ({
      status: 'error',
      message: 'GSM module not connected',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/gsm\/at$/,
    handler: ({ body }) => ({
      command: (body as { command: string }).command,
      response: ['ERROR: GSM module not connected (demo mode)'],
      success: false,
      error: 'Module disconnected',
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/gsm\/ports$/,
    handler: () => ({
      usb_ports: [],
      acm_ports: [],
      total: 0,
    }),
  },
]
