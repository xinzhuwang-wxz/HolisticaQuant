import type { LearningTopicsResponse, QueryResponse, ResearchTemplatesResponse } from '../types'

const DEFAULT_API_BASE = 'http://localhost:8000'

// Session ID管理（存储在localStorage）
const SESSION_ID_KEY = 'holistica_session_id'

export const getSessionId = (): string => {
  let sessionId = localStorage.getItem(SESSION_ID_KEY)
  if (!sessionId) {
    sessionId = crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem(SESSION_ID_KEY, sessionId)
  }
  return sessionId
}

interface RunQueryPayload {
  query: string
  scenarioOverride?: 'learning_workshop' | 'research_lab' | 'assistant'
  provider?: string | null
  returnTrace?: boolean
  context?: Record<string, unknown>
}

export const getApiBase = (): string => {
  const envBase = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_BASE_URL : undefined
  return (envBase as string | undefined)?.trim() || DEFAULT_API_BASE
}

export const getWebSocketBase = (): string => {
  const httpBase = getApiBase()
  if (httpBase.startsWith('https://')) {
    return `wss://${httpBase.slice('https://'.length)}`
  }
  if (httpBase.startsWith('http://')) {
    return `ws://${httpBase.slice('http://'.length)}`
  }
  return httpBase.replace(/^http/, 'ws')
}

export const runQuery = async (payload: RunQueryPayload): Promise<QueryResponse> => {
  const endpoint = `${getApiBase()}/api/query`
  const sessionId = getSessionId()

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Id': sessionId,
    },
    body: JSON.stringify({
      query: payload.query,
      provider: payload.provider,
      scenario_override: payload.scenarioOverride,
      return_trace: payload.returnTrace ?? false,
      context: payload.context,
    }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `请求失败，状态码 ${response.status}`)
  }

  const data = (await response.json()) as QueryResponse
  return data
}

export const fetchLearningTopics = async (): Promise<LearningTopicsResponse> => {
  const endpoint = `${getApiBase()}/api/scenarios/learning`
  const response = await fetch(endpoint, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `获取学习场景失败，状态码 ${response.status}`)
  }

  const data = (await response.json()) as LearningTopicsResponse
  return data
}

export const fetchResearchTemplates = async (): Promise<ResearchTemplatesResponse> => {
  const endpoint = `${getApiBase()}/api/scenarios/research`
  const response = await fetch(endpoint, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `获取投研模板失败，状态码 ${response.status}`)
  }

  const data = (await response.json()) as ResearchTemplatesResponse
  return data
}

// API密钥管理
export interface ApiKeyConfigResponse {
  configured_providers: string[]
  using_builtin: boolean
}

export const setApiKeys = async (keys: Record<string, string>): Promise<ApiKeyConfigResponse> => {
  const endpoint = `${getApiBase()}/api/config/keys`
  const sessionId = getSessionId()

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Session-Id': sessionId,
    },
    body: JSON.stringify({ keys }),
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `设置API密钥失败，状态码 ${response.status}`)
  }

  const data = (await response.json()) as ApiKeyConfigResponse
  return data
}

export const getApiKeysStatus = async (): Promise<ApiKeyConfigResponse> => {
  const endpoint = `${getApiBase()}/api/config/keys`
  const sessionId = getSessionId()

  const response = await fetch(endpoint, {
    method: 'GET',
    headers: {
      'X-Session-Id': sessionId,
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `获取API密钥状态失败，状态码 ${response.status}`)
  }

  const data = (await response.json()) as ApiKeyConfigResponse
  return data
}

export const clearApiKeys = async (): Promise<void> => {
  const endpoint = `${getApiBase()}/api/config/keys`
  const sessionId = getSessionId()

  const response = await fetch(endpoint, {
    method: 'DELETE',
    headers: {
      'X-Session-Id': sessionId,
    },
  })

  if (!response.ok) {
    const errorText = await response.text()
    throw new Error(errorText || `清除API密钥失败，状态码 ${response.status}`)
  }
}

