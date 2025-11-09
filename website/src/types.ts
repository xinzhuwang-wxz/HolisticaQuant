export interface NavigationProps {
  onNavigate: (page: 'landing' | 'learning' | 'research' | 'qa') => void
}

export interface TaskCard {
  id: string
  title: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimatedTime: string
  category: string
}

export interface ResearchTemplate {
  id: string
  name: string
  description: string
  fields: TemplateField[]
  icon: string
}

export interface TemplateField {
  id: string
  name: string
  type: 'text' | 'number' | 'select' | 'date'
  required: boolean
  placeholder?: string
  options?: string[]
}

export interface QAItem {
  id: string
  question: string
  answer: string
  sources: Source[]
  timestamp: Date
}

export interface Source {
  name: string
  url: string
  type: 'financial' | 'news' | 'report' | 'database'
}

export interface QueryResponse {
  scenario_type: 'learning_workshop' | 'research_lab' | 'assistant'
  plan?: Record<string, unknown> | null
  tickers: string[]
  plan_target_id?: string | null
  report: string
  metadata: Record<string, unknown>
  segments: Record<string, unknown>
  trace?: Record<string, unknown>[] | null
}