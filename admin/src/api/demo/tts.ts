import type { DemoRoute } from './types'
import { getStore } from './store'

const voices = [
  { id: 'gulya', name: 'Гуля', engine: 'xtts', description: 'XTTS v2 клонированный голос — дружелюбный женский', available: true, samples_count: 12, default: true },
  { id: 'lidia', name: 'Лидия', engine: 'xtts', description: 'XTTS v2 клонированный голос — строгий деловой', available: true, samples_count: 8, default: false },
  { id: 'dmitri', name: 'Дмитрий', engine: 'piper', description: 'Piper TTS (CPU) — мужской русский голос', available: true, samples_count: 0, default: false },
]

const builtinPresets: Record<string, { display_name: string; temperature: number; repetition_penalty: number; top_k: number; top_p: number; speed: number }> = {
  natural: { display_name: 'Натуральный', temperature: 0.65, repetition_penalty: 2.0, top_k: 50, top_p: 0.85, speed: 1.0 },
  expressive: { display_name: 'Выразительный', temperature: 0.85, repetition_penalty: 5.0, top_k: 80, top_p: 0.9, speed: 0.95 },
  fast: { display_name: 'Быстрый', temperature: 0.3, repetition_penalty: 10.0, top_k: 20, top_p: 0.7, speed: 1.2 },
}

// Minimal WAV header for demo audio (silence)
function createMinimalWav(): ArrayBuffer {
  const numSamples = 8000 // 0.5s at 16kHz
  const buffer = new ArrayBuffer(44 + numSamples * 2)
  const view = new DataView(buffer)
  // RIFF header
  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
  }
  writeString(0, 'RIFF')
  view.setUint32(4, 36 + numSamples * 2, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, 16000, true)
  view.setUint32(28, 32000, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeString(36, 'data')
  view.setUint32(40, numSamples * 2, true)
  // Silence (zeros)
  return buffer
}

export const ttsRoutes: DemoRoute[] = [
  {
    method: 'GET',
    pattern: /^\/admin\/voices$/,
    handler: () => ({
      voices,
      current: { engine: 'xtts', voice: 'gulya' },
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/voice$/,
    handler: () => ({ engine: 'xtts', voice: 'gulya' }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/voice$/,
    handler: ({ body }) => {
      const { voice } = body as { voice: string }
      const v = voices.find(v => v.id === voice)
      return { status: 'ok', engine: v?.engine || 'xtts', voice }
    },
  },
  {
    method: 'POST',
    pattern: /^\/admin\/voice\/test$/,
    handler: () => '__BLOB__',
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts\/xtts\/params$/,
    handler: () => ({
      default_preset: 'natural',
      current_params: {
        temperature: 0.65,
        repetition_penalty: 2.0,
        top_k: 50,
        top_p: 0.85,
        speed: 1.0,
        gpt_cond_len: 30,
        gpt_cond_chunk_len: 4,
      },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts\/xtts\/params$/,
    handler: ({ body }) => ({
      status: 'ok',
      params: body,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts\/piper\/params$/,
    handler: () => ({
      speed: 1.0,
      voices: { dmitri: { name: 'Дмитрий', language: 'ru' } },
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts\/piper\/params$/,
    handler: ({ body }) => ({
      status: 'ok',
      speed: (body as { speed: number }).speed,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts\/presets$/,
    handler: () => ({
      presets: builtinPresets,
      current: 'natural',
    }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts\/preset$/,
    handler: ({ body }) => ({
      status: 'ok',
      preset: (body as { preset: string }).preset,
    }),
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts\/presets\/custom$/,
    handler: () => ({ presets: getStore().customTtsPresets }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts\/presets\/custom$/,
    handler: ({ body }) => {
      const { name, params } = body as { name: string; params: Record<string, number> }
      getStore().customTtsPresets[name] = params
      return { status: 'ok', preset: name }
    },
  },
  {
    method: 'PUT',
    pattern: /^\/admin\/tts\/presets\/custom\/([^/]+)$/,
    handler: ({ matches, body }) => {
      const { params } = body as { name: string; params: Record<string, number> }
      getStore().customTtsPresets[matches[1]] = params
      return { status: 'ok', preset: matches[1] }
    },
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/tts\/presets\/custom\/([^/]+)$/,
    handler: ({ matches }) => {
      delete getStore().customTtsPresets[matches[1]]
      return { status: 'ok', deleted: matches[1] }
    },
  },
  {
    method: 'GET',
    pattern: /^\/admin\/tts\/cache$/,
    handler: () => ({ cache_size: 47, active_sessions: 2 }),
  },
  {
    method: 'DELETE',
    pattern: /^\/admin\/tts\/cache$/,
    handler: () => ({ status: 'ok', cleared_items: 47 }),
  },
  {
    method: 'POST',
    pattern: /^\/admin\/tts\/test$/,
    handler: () => '__BLOB__',
  },
]

export { createMinimalWav }
