import type { DemoRoute } from './types'

export const sttRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/stt\/status$/,
    handler: () => ({
      vosk_available: true,
      whisper_available: true,
      vosk_model: 'vosk-model-ru-0.42',
      whisper_model: 'small',
      unified_available: true,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/stt\/models$/,
    handler: () => ({
      models: [
        { name: 'vosk-model-ru-0.42', path: 'models/vosk/vosk-model-ru-0.42', size_mb: 1800, language: 'ru' },
        { name: 'whisper-small', path: 'models/whisper/small', size_mb: 461, language: 'multilingual' },
      ],
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/stt\/transcribe$/,
    handler: () => ({
      text: 'Привет, это тестовое распознавание речи в демо-режиме.',
      confidence: 0.92,
      duration: 2.4,
      engine: 'vosk',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/stt\/test$/,
    handler: () => ({
      original_text: 'Привет, это тест распознавания речи',
      recognized_text: 'Привет это тест распознавания речи',
      match: true,
      duration_seconds: 3.2,
    }),
  },
]
