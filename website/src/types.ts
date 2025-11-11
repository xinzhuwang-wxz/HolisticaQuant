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

export type ResearchTemplateType = 'valuation' | 'industry' | 'risk' | 'custom'

export interface ResearchTemplateInputOption {
  label: string
  value: string
}

export interface ResearchTemplateInput {
  field: string
  label: string
  type?: 'text' | 'number' | 'select'
  unit?: string
  default?: string | number
  default_value?: string | number
  placeholder?: string
  options?: ResearchTemplateInputOption[]
}

export interface ResearchTemplateHighlight {
  label: string
  value: string
  source?: string
}

export interface ResearchTemplate {
  id: string
  title: string
  template_type: ResearchTemplateType
  ticker?: string
  description: string
  hero_metrics?: ResearchTemplateHighlight[]
  required_inputs: ResearchTemplateInput[]
  optional_inputs?: ResearchTemplateInput[]
  analysis_focus?: string[]
  verification_sources?: string[]
  prompt_lead?: string
  cta_label?: string
}

export interface ResearchTemplatesResponse {
  templates: ResearchTemplate[]
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

export interface WorkflowStep {
  agent: string
  tool: string
  summary: string
  timestamp?: string
}

export interface LearningTopicKeyDataPoint {
  label: string
  value: string
  source?: string
}

export interface LearningTopicTaskInput {
  label: string
  value?: number
  unit?: string
  placeholder?: string
}

export interface LearningTopicTaskConfig {
  prompt: string
  calculator_inputs: LearningTopicTaskInput[]
  formula?: string
  expected_result?: string
  explanation?: string
}

export interface LearningTopicValidation {
  reference_data?: string
  insight?: string
}

export interface LearningTopic {
  id: string
  title: string
  knowledge_point: string
  category: string[]
  scenario_summary?: string
  key_data_points: LearningTopicKeyDataPoint[]
  learning_objectives: string[]
  difficulty?: 'beginner' | 'intermediate' | 'advanced'
  estimated_time?: string
  task: LearningTopicTaskConfig
  validation?: LearningTopicValidation
  recommended_followups?: string[]
}

export interface LearningTopicsResponse {
  topics: LearningTopic[]
}

export interface LearningWorkshopMetadata {
  scenario_id?: string
  knowledge_point?: string
  learning_objectives?: string[]
  task_steps?: string[]
  validation_logic?: string
  ai_guidance?: string
  [key: string]: unknown
}

export interface DataAnalysisSummary {
  updated_at?: string
  analysis_preview?: string
  highlights?: string[]
  tools?: Array<Record<string, unknown>>
  full_report?: string
  [key: string]: unknown
}

export interface StrategySummary {
  updated_at?: string
  recommendation?: string
  confidence?: string | number
  target_price?: string
  position_suggestion?: string
  time_horizon?: string
  entry_conditions?: string[]
  exit_conditions?: string[]
  rationale?: string
  report_preview?: string
  highlights?: string[]
  full_report?: string
  tools?: Array<Record<string, unknown>>
  [key: string]: unknown
}

export interface QueryMetadata {
  learning_workshop?: LearningWorkshopMetadata
  data_analysis_summary?: DataAnalysisSummary
  strategy_summary?: StrategySummary
  [key: string]: unknown
}

export interface QueryResponse {
  scenario_type: 'learning_workshop' | 'research_lab' | 'assistant'
  plan?: Record<string, unknown> | null
  tickers: string[]
  plan_target_id?: string | null
  report: string
  metadata: QueryMetadata
  segments: Record<string, unknown>
  trace?: Record<string, unknown>[] | null
}