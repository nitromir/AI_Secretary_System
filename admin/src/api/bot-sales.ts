// Bot Sales API client — CRUD for all sales bot entities
import { api } from './client'

// ============== Types ==============

export interface AgentPrompt {
  id: number
  bot_id: string
  prompt_key: string
  name: string
  description?: string
  system_prompt: string
  temperature: number
  max_tokens: number
  enabled: boolean
  order: number
  created?: string
  updated?: string
}

export interface QuizQuestion {
  id: number
  bot_id: string
  question_key: string
  text: string
  order: number
  enabled: boolean
  options: Array<{ label: string; value: string; icon?: string }>
  created?: string
  updated?: string
}

export interface Segment {
  id: number
  bot_id: string
  segment_key: string
  name: string
  description?: string
  path: string
  match_rules: Record<string, string>
  priority: number
  agent_prompt_key?: string
  enabled: boolean
  created?: string
}

export interface FollowupRule {
  id: number
  bot_id: string
  name: string
  trigger: string
  delay_hours: number
  segment_filter?: string
  message_template: string
  buttons: Array<{ text: string; callback_data: string }>
  max_sends: number
  enabled: boolean
  order: number
  created?: string
  updated?: string
}

export interface Testimonial {
  id: number
  bot_id: string
  text: string
  author: string
  rating: number
  enabled: boolean
  order: number
  created?: string
}

export interface HardwareSpec {
  id: number
  bot_id: string
  gpu_name: string
  gpu_vram_gb: number
  gpu_family: string
  recommended_llm: string
  recommended_tts: string
  recommended_stt: string
  quality_stars: number
  speed_note?: string
  notes?: string
  enabled: boolean
  order: number
}

export interface AbTest {
  id: number
  bot_id: string
  name: string
  test_key: string
  variants: Record<string, unknown>
  metric: string
  min_sample: number
  active: boolean
  results?: Record<string, unknown>
  created?: string
  updated?: string
}

export interface Subscriber {
  id: number
  bot_id: string
  user_id: number
  subscribed: boolean
  subscribed_at?: string
  unsubscribed_at?: string
}

export interface GithubConfig {
  id?: number
  bot_id: string
  repo_owner: string
  repo_name: string
  github_token?: string
  webhook_secret?: string
  comment_enabled: boolean
  broadcast_enabled: boolean
  comment_prompt?: string
  broadcast_prompt?: string
  events: string[]
  created?: string
  updated?: string
}

export interface FunnelData {
  [stage: string]: number
}

// ============== API ==============

function base(instanceId: string) {
  return `/admin/telegram/instances/${instanceId}`
}

export const botSalesApi = {
  // --- Agent Prompts ---
  listPrompts: (id: string) =>
    api.get<{ prompts: AgentPrompt[] }>(`${base(id)}/prompts`),
  createPrompt: (id: string, data: Partial<AgentPrompt>) =>
    api.post<{ prompt: AgentPrompt }>(`${base(id)}/prompts`, data),
  updatePrompt: (id: string, promptId: number, data: Partial<AgentPrompt>) =>
    api.put<{ prompt: AgentPrompt }>(`${base(id)}/prompts/${promptId}`, data),
  deletePrompt: (id: string, promptId: number) =>
    api.delete<{ status: string }>(`${base(id)}/prompts/${promptId}`),

  // --- Quiz Questions ---
  listQuiz: (id: string) =>
    api.get<{ questions: QuizQuestion[] }>(`${base(id)}/quiz`),
  createQuiz: (id: string, data: Partial<QuizQuestion>) =>
    api.post<{ question: QuizQuestion }>(`${base(id)}/quiz`, data),
  updateQuiz: (id: string, questionId: number, data: Partial<QuizQuestion>) =>
    api.put<{ question: QuizQuestion }>(`${base(id)}/quiz/${questionId}`, data),
  deleteQuiz: (id: string, questionId: number) =>
    api.delete<{ status: string }>(`${base(id)}/quiz/${questionId}`),

  // --- Segments ---
  listSegments: (id: string) =>
    api.get<{ segments: Segment[] }>(`${base(id)}/segments`),
  createSegment: (id: string, data: Partial<Segment>) =>
    api.post<{ segment: Segment }>(`${base(id)}/segments`, data),
  updateSegment: (id: string, segmentId: number, data: Partial<Segment>) =>
    api.put<{ segment: Segment }>(`${base(id)}/segments/${segmentId}`, data),
  deleteSegment: (id: string, segmentId: number) =>
    api.delete<{ status: string }>(`${base(id)}/segments/${segmentId}`),

  // --- Followup Rules ---
  listFollowups: (id: string) =>
    api.get<{ rules: FollowupRule[] }>(`${base(id)}/followups`),
  createFollowup: (id: string, data: Partial<FollowupRule>) =>
    api.post<{ rule: FollowupRule }>(`${base(id)}/followups`, data),
  updateFollowup: (id: string, ruleId: number, data: Partial<FollowupRule>) =>
    api.put<{ rule: FollowupRule }>(`${base(id)}/followups/${ruleId}`, data),
  deleteFollowup: (id: string, ruleId: number) =>
    api.delete<{ status: string }>(`${base(id)}/followups/${ruleId}`),

  // --- Testimonials ---
  listTestimonials: (id: string) =>
    api.get<{ testimonials: Testimonial[] }>(`${base(id)}/testimonials`),
  createTestimonial: (id: string, data: Partial<Testimonial>) =>
    api.post<{ testimonial: Testimonial }>(`${base(id)}/testimonials`, data),
  updateTestimonial: (id: string, testimonialId: number, data: Partial<Testimonial>) =>
    api.put<{ testimonial: Testimonial }>(`${base(id)}/testimonials/${testimonialId}`, data),
  deleteTestimonial: (id: string, testimonialId: number) =>
    api.delete<{ status: string }>(`${base(id)}/testimonials/${testimonialId}`),

  // --- Hardware Specs ---
  listHardware: (id: string) =>
    api.get<{ specs: HardwareSpec[] }>(`${base(id)}/hardware`),
  createHardware: (id: string, data: Partial<HardwareSpec>) =>
    api.post<{ spec: HardwareSpec }>(`${base(id)}/hardware`, data),
  updateHardware: (id: string, specId: number, data: Partial<HardwareSpec>) =>
    api.put<{ spec: HardwareSpec }>(`${base(id)}/hardware/${specId}`, data),
  deleteHardware: (id: string, specId: number) =>
    api.delete<{ status: string }>(`${base(id)}/hardware/${specId}`),

  // --- A/B Tests ---
  listAbTests: (id: string) =>
    api.get<{ tests: AbTest[] }>(`${base(id)}/abtests`),
  createAbTest: (id: string, data: Partial<AbTest>) =>
    api.post<{ test: AbTest }>(`${base(id)}/abtests`, data),
  updateAbTest: (id: string, testId: number, data: Partial<AbTest>) =>
    api.put<{ test: AbTest }>(`${base(id)}/abtests/${testId}`, data),
  deleteAbTest: (id: string, testId: number) =>
    api.delete<{ status: string }>(`${base(id)}/abtests/${testId}`),

  // --- Subscribers ---
  listSubscribers: (id: string) =>
    api.get<{ subscribers: Subscriber[] }>(`${base(id)}/subscribers`),
  getSubscriberStats: (id: string) =>
    api.get<{ stats: { total_active: number } }>(`${base(id)}/subscribers/stats`),

  // --- GitHub Config ---
  getGithubConfig: (id: string) =>
    api.get<{ config: GithubConfig | null }>(`${base(id)}/github-config`),
  saveGithubConfig: (id: string, data: Partial<GithubConfig>) =>
    api.put<{ config: GithubConfig }>(`${base(id)}/github-config`, data),

  // --- Funnel / Events ---
  getFunnel: (id: string, days = 30) =>
    api.get<{ funnel: FunnelData }>(`${base(id)}/funnel?days=${days}`),
  getDailyReport: (id: string) =>
    api.get<{ report: { funnel: FunnelData; subscribers: number; segments: Record<string, number> } }>(
      `${base(id)}/funnel/daily`
    ),

  // --- Users ---
  listUsers: (id: string, segment?: string, state?: string) => {
    const params = new URLSearchParams()
    if (segment) params.set('segment', segment)
    if (state) params.set('state', state)
    const qs = params.toString()
    return api.get<{ users: Array<Record<string, unknown>> }>(
      `${base(id)}/users${qs ? '?' + qs : ''}`
    )
  },
}
