import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Download,
  CheckCircle,
  Sparkles,
  TrendingUp,
  Layers,
  ShieldCheck,
  BarChart3,
  LineChart,
} from 'lucide-react'
import { fetchResearchTemplates, getWebSocketBase, runQuery } from '../lib/apiClient'
import type {
  QueryResponse,
  ResearchTemplate,
  ResearchTemplateInput,
  StrategySummary,
  DataAnalysisSummary,
  ResearchTemplateHighlight,
} from '../types'

const CUSTOM_TEMPLATE: ResearchTemplate = {
  id: 'custom_template',
  title: '自定义策略草稿',
  template_type: 'custom',
  description: '自由输入标的、假设与关注点，快速生成投资策略草稿。',
  required_inputs: [
    {
      field: 'custom_subject',
      label: '标的 / 主题',
      type: 'text',
      placeholder: '如：300750.SZ 宁德时代',
    },
    {
      field: 'custom_focus',
      label: '关注角度',
      type: 'text',
      placeholder: '估值修复、订单动能、政策催化…',
    },
  ],
  optional_inputs: [
    {
      field: 'custom_questions',
      label: '想回答的问题（逗号分隔）',
      type: 'text',
      placeholder: '目标价区间, 风险点, 关键监控指标',
    },
  ],
  analysis_focus: [
    '先梳理最新数据与事件',
    '再提出策略与风险建议',
    '最后输出投资建议 JSON',
  ],
  prompt_lead:
    '请基于上述自定义输入生成结构化投资策略报告，包括：市场概览、数据要点、策略建议、风险提示与最终投资建议 JSON。',
  cta_label: '策略草稿',
}

type TimelineEvent = {
  id: string
  title: string
  content?: string
}

type TemplateVisual = {
  gradient: string
  Icon: typeof TrendingUp
  badge: string
}

const TEMPLATE_VISUALS: Record<string, TemplateVisual> = {
  valuation: { gradient: 'from-blue-500 to-blue-600', Icon: TrendingUp, badge: '估值' },
  industry: { gradient: 'from-emerald-500 to-teal-600', Icon: Layers, badge: '行业' },
  risk: { gradient: 'from-orange-500 to-red-500', Icon: ShieldCheck, badge: '风险' },
  custom: { gradient: 'from-purple-500 to-pink-500', Icon: Sparkles, badge: '自定义' },
}

const TIMEWRITER_INTERVAL_MS = 24
const TIMELINE_SWITCH_DELAY_MS = 240
const TIMELINE_CHUNK_LENGTH = 540

const highlightText = (content?: string, fallback?: string) =>
  content?.trim().split(/\n+/).filter(Boolean) ?? (fallback ? [fallback] : [])

const ResearchLab: React.FC = () => {
  const navigate = useNavigate()
  const [templates, setTemplates] = useState<ResearchTemplate[]>([])
  const [loadingTemplates, setLoadingTemplates] = useState(true)
  const [templatesError, setTemplatesError] = useState<string | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('')
  const [inputValues, setInputValues] = useState<Record<string, string>>({})
  const templateDraftsRef = useRef<Record<string, Record<string, string>>>({})
  const templateMetaRef = useRef<Record<string, { target: string; focus: string; notes: string }>>({})
  const [userNotes, setUserNotes] = useState('')
  const [userTarget, setUserTarget] = useState('')
  const [userFocus, setUserFocus] = useState('')

  const [isGenerating, setIsGenerating] = useState(false)
  const [apiResult, setApiResult] = useState<QueryResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [currentTimelineEvent, setCurrentTimelineEvent] = useState<TimelineEvent | null>(null)
  const [timelineRenderedContent, setTimelineRenderedContent] = useState('')
  const [metadataSnapshot, setMetadataSnapshot] = useState<{
    strategy?: StrategySummary | null
    dataAnalysis?: DataAnalysisSummary | null
  }>({})

  const wsRef = useRef<WebSocket | null>(null)
  const timelineQueueRef = useRef<TimelineEvent[]>([])
  const timelineProcessingRef = useRef(false)
  const typewriterRef = useRef<number | null>(null)

  const stopTypewriter = useCallback(() => {
    if (typewriterRef.current !== null) {
      window.clearTimeout(typewriterRef.current)
      typewriterRef.current = null
    }
  }, [])

  const resetTimeline = useCallback(() => {
    stopTypewriter()
    timelineQueueRef.current = []
    timelineProcessingRef.current = false
    setCurrentTimelineEvent(null)
    setTimelineRenderedContent('')
  }, [stopTypewriter])

  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const response = await fetchResearchTemplates()
        setTemplates(response.templates ?? [])
        if ((response.templates ?? []).length) {
          setSelectedTemplateId(response.templates[0].id)
        }
      } catch (error) {
        console.error('fetchResearchTemplates error', error)
        setTemplatesError(error instanceof Error ? error.message : '无法获取投研模板')
      } finally {
        setLoadingTemplates(false)
      }
    }

    loadTemplates()
  }, [])

  const templateList = useMemo(() => {
    return [...templates, CUSTOM_TEMPLATE]
  }, [templates])

  useEffect(() => {
    if (!selectedTemplateId && templateList.length > 0) {
      setSelectedTemplateId(templateList[0].id)
    }
  }, [templateList, selectedTemplateId])

  const selectedTemplate = useMemo<ResearchTemplate | null>(() => {
    return templateList.find((tpl) => tpl.id === selectedTemplateId) ?? null
  }, [templateList, selectedTemplateId])

  const deriveDefaultInputs = useCallback((template: ResearchTemplate | null) => {
    if (!template) return {}
    const defaults: Record<string, string> = {}
    const collect = (input: ResearchTemplateInput) => {
      const definedDefault =
        input.default !== undefined && input.default !== null
          ? input.default
          : input.default_value !== undefined && input.default_value !== null
          ? input.default_value
          : undefined
      if (definedDefault !== undefined) {
        defaults[input.field] = String(definedDefault)
      } else {
        defaults[input.field] = ''
      }
    }
    template.required_inputs.forEach(collect)
    ;(template.optional_inputs ?? []).forEach(collect)
    return defaults
  }, [])

  useEffect(() => {
    if (!selectedTemplate) return
    const draft = templateDraftsRef.current[selectedTemplate.id]
    if (draft) {
      setInputValues(draft)
    } else {
      const defaults = deriveDefaultInputs(selectedTemplate)
      templateDraftsRef.current[selectedTemplate.id] = defaults
      setInputValues(defaults)
    }

    const metaDraft = templateMetaRef.current[selectedTemplate.id]
    const titleSuffix = selectedTemplate.title.includes('·')
      ? selectedTemplate.title.split('·').slice(-1)[0]?.trim()
      : selectedTemplate.title
    const defaultTarget =
      metaDraft?.target ??
      (selectedTemplate.template_type === 'custom'
        ? ''
        : [selectedTemplate.ticker, titleSuffix].filter(Boolean).join(' '))

    const defaultFocusByType: Record<string, string> = {
      valuation: '聚焦估值',
      industry: '聚焦行业板块',
      risk: '聚焦风险',
    }
    const defaultFocus =
      metaDraft?.focus ??
      (selectedTemplate.template_type !== 'custom'
        ? defaultFocusByType[selectedTemplate.template_type] ?? ''
        : '')

    setUserTarget(defaultTarget)
    setUserFocus(defaultFocus)
    setUserNotes(metaDraft?.notes ?? '')

    if (!metaDraft) {
      templateMetaRef.current[selectedTemplate.id] = { target: defaultTarget, focus: defaultFocus, notes: '' }
    }

    setApiResult(null)
    setErrorMessage(null)
    resetTimeline()
  }, [selectedTemplate, deriveDefaultInputs, resetTimeline])

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      stopTypewriter()
    }
  }, [stopTypewriter])

  const processTimelineQueue = useCallback(() => {
    if (timelineProcessingRef.current) return
    const nextEvent = timelineQueueRef.current.shift()
    if (!nextEvent) return

    timelineProcessingRef.current = true
    setCurrentTimelineEvent(nextEvent)

    if (!nextEvent.content) {
      setTimelineRenderedContent('')
      typewriterRef.current = window.setTimeout(() => {
        typewriterRef.current = null
        timelineProcessingRef.current = false
        processTimelineQueue()
      }, TIMELINE_SWITCH_DELAY_MS)
      return
    }

    setTimelineRenderedContent('')
    const content = nextEvent.content

    const runTypewriter = (index: number) => {
      setTimelineRenderedContent(content.slice(0, index + 1))
      if (index + 1 < content.length) {
        typewriterRef.current = window.setTimeout(() => runTypewriter(index + 1), TIMEWRITER_INTERVAL_MS)
      } else {
        typewriterRef.current = window.setTimeout(() => {
          typewriterRef.current = null
          timelineProcessingRef.current = false
          processTimelineQueue()
        }, TIMELINE_SWITCH_DELAY_MS)
      }
    }

    typewriterRef.current = window.setTimeout(() => runTypewriter(0), TIMEWRITER_INTERVAL_MS)
  }, [])

  const pushTimelineEvent = useCallback(
    (title: string, content?: string) => {
      const enqueue = (chunkTitle: string, chunkContent?: string) => {
        timelineQueueRef.current.push({
          id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
          title: chunkTitle,
          content: chunkContent,
        })
      }

      if (content && content.length > TIMELINE_CHUNK_LENGTH) {
        const segments: string[] = []
        const paragraphs = content.split(/\n\n+/)
        let buffer = ''
        const flushBuffer = () => {
          if (buffer.trim()) {
            segments.push(buffer.trim())
          }
          buffer = ''
        }
        paragraphs.forEach((para, index) => {
          const candidate = buffer ? `${buffer}\n\n${para}` : para
          if (candidate.length <= TIMELINE_CHUNK_LENGTH) {
            buffer = candidate
          } else {
            if (buffer) {
              flushBuffer()
            }
            if (para.length <= TIMELINE_CHUNK_LENGTH) {
              buffer = para
            } else {
              let pointer = 0
              while (pointer < para.length) {
                const slice = para.slice(pointer, pointer + TIMELINE_CHUNK_LENGTH)
                segments.push(slice.trim())
                pointer += TIMELINE_CHUNK_LENGTH
              }
              buffer = ''
            }
          }
          if (index === paragraphs.length - 1 && buffer) {
            flushBuffer()
          }
        })

        segments.forEach((segment, idx) => {
          const suffix = idx === 0 ? '' : ` · 续${idx + 1}`
          enqueue(`${title}${suffix}`, segment)
        })
      } else {
        enqueue(title, content)
      }

      processTimelineQueue()
    },
    [processTimelineQueue]
  )

  const formatInputSummary = useCallback(
    (template: ResearchTemplate, values: Record<string, string>): string => {
      const resolveLabel = (fieldId: string) => {
        const allFields = [...template.required_inputs, ...(template.optional_inputs ?? [])]
        return allFields.find((item) => item.field === fieldId)
      }
      const lines = Object.entries(values)
        .filter(([, value]) => Boolean(value?.toString().trim()))
        .map(([fieldId, value]) => {
          const field = resolveLabel(fieldId)
          const unit = field?.unit ? ` ${field.unit}` : ''
          const label = field?.label ?? fieldId
          return `${label}: ${value}${unit}`
        })
      return lines.length ? lines.join('\n') : '（未提供，使用模板默认假设）'
    },
    []
  )

  const buildPrompt = useCallback(
    (
      template: ResearchTemplate,
      values: Record<string, string>,
      target: string,
      focus: string,
      notes: string
    ) => {
      const focusLines = template.analysis_focus
        ? template.analysis_focus.map((item, idx) => `${idx + 1}. ${item}`).join('\n')
        : ''
      const verificationLines = template.verification_sources
        ? template.verification_sources.map((item) => `- ${item}`).join('\n')
        : ''

      return [
        `投研模板ID：${template.id}`,
        `模板名称：${template.title}`,
        `模板类型：${template.template_type}`,
        template.ticker ? `核心标的：${template.ticker}` : '',
        target?.trim() ? `用户指定标的：${target.trim()}` : '',
        focus?.trim() ? `关注角度：${focus.trim()}` : '',
        `模板描述：${template.description}`,
        focusLines ? `分析重点：\n${focusLines}` : '',
        verificationLines ? `验证提示：\n${verificationLines}` : '',
        `输入参数：\n${formatInputSummary(template, values)}`,
        notes?.trim() ? `团队备注：${notes.trim()}` : '',
        template.prompt_lead ??
          '请基于上述信息生成结构化投研报告，包含：市场/行业概览、关键指标拆解、风险提示、投资建议与下一步跟踪要点。',
      ]
        .filter(Boolean)
        .join('\n\n')
    },
    [formatInputSummary]
  )

  const buildContextPayload = useCallback(
    (
      template: ResearchTemplate,
      values: Record<string, string>,
      target: string,
      focus: string,
      notes: string
    ) => {
      const collectFields = (inputList: ResearchTemplateInput[]) =>
        inputList.map((input) => ({
          field: input.field,
          label: input.label,
          unit: input.unit,
          type: input.type,
          value: values[input.field] ?? '',
        }))

      return {
        template_id: template.id,
        template_type: template.template_type,
        ticker: template.ticker,
        inputs: {
          required: collectFields(template.required_inputs),
          optional: collectFields(template.optional_inputs ?? []),
        },
        user_target: target?.trim() || template.ticker,
        cta_label: template.cta_label,
        focus: focus?.trim() || undefined,
        notes: notes?.trim() || undefined,
      }
    },
    []
  )

  const buildFallbackReport = useCallback(
    (template: ResearchTemplate | null, values: Record<string, string>): string => {
      if (!template) return '【提示】模板未加载成功，展示示例草稿。'
      const lines: string[] = []
      lines.push(`【模板】${template.title}`)
      if (template.ticker) {
        lines.push(`【标的】${template.ticker}`)
      }
      lines.push('【输入假设】')
      lines.push(formatInputSummary(template, values))
      lines.push('')
      lines.push('【概要】本报告基于示例参数生成，请更新假设后重新生成正式稿。')
      return lines.join('\n')
    },
    [formatInputSummary]
  )

  const applyFinalResponse = useCallback(
    (response: QueryResponse, template: ResearchTemplate | null, completionMessage?: string) => {
      setApiResult(response)
      const strategySummary = response.metadata?.strategy_summary ?? null
      const dataSummary = response.metadata?.data_analysis_summary ?? null
      setMetadataSnapshot({ strategy: strategySummary, dataAnalysis: dataSummary })

      const followUpEvents: TimelineEvent[] = []

      if (dataSummary) {
        const preview = dataSummary.analysis_preview || dataSummary.full_report
        if (preview) {
          followUpEvents.push({
            id: `data-${Date.now()}`,
            title: '数据分析完成',
            content: preview,
          })
        }
      }

      if (strategySummary) {
        const rec = strategySummary.recommendation ? `建议：${strategySummary.recommendation}` : ''
        const target = strategySummary.target_price ? `目标价：${strategySummary.target_price}` : ''
        const confidence = strategySummary.confidence ? `置信度：${strategySummary.confidence}` : ''
        const summaryLine = [rec, target, confidence].filter(Boolean).join('｜')
        if (summaryLine) {
          followUpEvents.push({
            id: `strategy-${Date.now()}`,
            title: '策略建议完成',
            content: summaryLine,
          })
        }
      }

      if (followUpEvents.length) {
        timelineQueueRef.current.push(...followUpEvents)
        processTimelineQueue()
      }

      pushTimelineEvent(template?.cta_label ? `${template.cta_label}完成` : '投研报告已生成', completionMessage)
      setIsGenerating(false)
    },
    [processTimelineQueue, pushTimelineEvent]
  )

  const handleGenerate = useCallback(async () => {
    if (!selectedTemplate) return

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    resetTimeline()
    setIsGenerating(true)
    setApiResult(null)
    setErrorMessage(null)

    templateDraftsRef.current[selectedTemplate.id] = { ...inputValues }
    templateMetaRef.current[selectedTemplate.id] = {
      target: userTarget,
      focus: userFocus,
      notes: userNotes,
    }

    pushTimelineEvent('准备投研任务', `正在编排 ${selectedTemplate.title} 所需指标…`)
    pushTimelineEvent('数据分析阶段', '正在聚合行情、财务与行业数据…')
    pushTimelineEvent('策略评估阶段', '正在组合策略亮点与风险提示…')
    pushTimelineEvent('生成投资建议', '整理最终建议…')

    const prompt = buildPrompt(selectedTemplate, inputValues, userTarget, userFocus, userNotes)
    const contextPayload = buildContextPayload(selectedTemplate, inputValues, userTarget, userFocus, userNotes)

    const httpPayload = {
      query: prompt,
      scenarioOverride: 'research_lab' as const,
      context: contextPayload,
    }

    const wsPayload = {
      query: prompt,
      scenario_override: 'research_lab',
      context: contextPayload,
    }

    let finalReceived = false
    let fallbackTriggered = false

    const fallbackToHttp = async (reason?: string) => {
      if (fallbackTriggered || finalReceived) return
      fallbackTriggered = true
      if (reason) {
        pushTimelineEvent('切换模式', reason)
      }
      try {
        const response = await runQuery(httpPayload)
        finalReceived = true
        applyFinalResponse(response, selectedTemplate, 'HTTP 模式下完成分析。')
      } catch (error) {
        console.error('ResearchLab fallback error:', error)
        const message = error instanceof Error ? error.message : '请求失败，请稍后再试。'
        setErrorMessage(message)
        pushTimelineEvent('请求失败', message)
        setIsGenerating(false)
      }
    }

    try {
      const socket = new WebSocket(`${getWebSocketBase()}/api/query/stream`)
      wsRef.current = socket

      socket.onopen = () => {
        pushTimelineEvent('实时通道已建立', 'AI 正在生成投研报告…')
        socket.send(JSON.stringify(wsPayload))
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as { type: string; [key: string]: any }
          // 如果已经收到最终内容，停止处理流式事件
          if (finalReceived && data.type !== 'final' && data.type !== 'error') {
            return
          }
          
          if (data.type === 'status') {
            pushTimelineEvent('进度更新', data.message)
          } else if (data.type === 'timeline') {
            pushTimelineEvent(data.title, data.content)
          } else if (data.type === 'final') {
            finalReceived = true
            // 立即停止流式输出
            stopTypewriter()
            const response = data.payload as QueryResponse
            applyFinalResponse(response, selectedTemplate)
            socket.close()
          } else if (data.type === 'error') {
            setErrorMessage(data.message)
            pushTimelineEvent('请求失败', data.message)
            setIsGenerating(false)
            socket.close()
          }
        } catch (err) {
          console.error('ResearchLab stream parse error', err)
        }
      }

      socket.onerror = () => {
        void fallbackToHttp('WebSocket 连接异常，改用普通模式。')
      }

      socket.onclose = () => {
        wsRef.current = null
        if (!finalReceived) {
          void fallbackToHttp()
        }
      }
    } catch (error) {
      console.error('ResearchLab websocket init error:', error)
      await fallbackToHttp('无法建立实时连接，改用普通模式。')
    }
  }, [
    applyFinalResponse,
    buildContextPayload,
    buildPrompt,
    userNotes,
    inputValues,
    pushTimelineEvent,
    resetTimeline,
    selectedTemplate,
    userTarget,
    userFocus,
  ])

  const handleInputChange = useCallback(
    (field: string, value: string) => {
      setInputValues((prev) => {
        const next = { ...prev, [field]: value }
        if (selectedTemplate) {
          templateDraftsRef.current[selectedTemplate.id] = next
        }
        return next
      })
    },
    [selectedTemplate]
  )

  const handleDownload = useCallback(() => {
    const template = selectedTemplate
    const reportContent = apiResult?.report ?? buildFallbackReport(template, inputValues)
    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${template?.ticker ?? 'research'}_strategy.txt`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [apiResult?.report, buildFallbackReport, inputValues, selectedTemplate])

  const computePeValue = useMemo(() => {
    if (!selectedTemplate || selectedTemplate.template_type !== 'valuation') return null
    const spotPrice = Number(inputValues['spot_price']) || NaN
    const eps = Number(inputValues['eps']) || NaN
    if (!Number.isFinite(spotPrice) || !Number.isFinite(eps) || eps === 0) {
      return null
    }
    return (spotPrice / eps).toFixed(2)
  }, [inputValues, selectedTemplate])

  const dataAnalysisSegment =
    typeof apiResult?.segments?.data_analysis === 'string' ? (apiResult?.segments?.data_analysis as string) : undefined

  const finalReportParagraphs = useMemo(() => {
    const report = apiResult?.report ?? buildFallbackReport(selectedTemplate, inputValues)
    return report
      .split(/\n{2,}/)
      .map((para) => para.trim())
      .filter(Boolean)
  }, [apiResult?.report, buildFallbackReport, inputValues, selectedTemplate])

  const scenarioBadges = useMemo(() => {
    if (!selectedTemplate) return []
    const badges: { label: string; value: string }[] = []

    const templateMetrics = (selectedTemplate.hero_metrics ?? []) as ResearchTemplateHighlight[]
    templateMetrics.forEach((metric) => {
      if (metric.label && metric.value) {
        badges.push({ label: metric.label, value: metric.value })
      }
    })

    if (userTarget || selectedTemplate.ticker) {
      badges.push({ label: '任务标的', value: userTarget || selectedTemplate.ticker || '' })
    }

    if (userFocus) {
      badges.push({ label: '关注角度', value: userFocus })
    }

    if (badges.length === 0 && selectedTemplate.description) {
      badges.push({ label: '场景简介', value: selectedTemplate.description })
    }

    return badges.slice(0, 4)
  }, [selectedTemplate, userFocus, userTarget])

  return (
    <div className="min-h-screen w-full relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-green-50 via-white to-blue-50 noise-bg">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(42,199,165,0.05),transparent_50%)]" />
      </div>

      <div className="relative z-10 p-4 sm:px-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-600 hover:text-primary-600 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Home
        </button>
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 sm:px-6 lg:px-8 pb-12">
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-full max-w-6xl"
        >
          <div className="text-center mb-12">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-display font-bold text-gray-900 mb-4">
              投资策略实验室
            </h1>
            <p className="text-lg sm:text-xl text-slate-600">
              三个策略案例 + 自定义任务，让 A 股策略报告开箱即用
            </p>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-[280px_minmax(0,1.4fr)_320px] gap-6 xl:gap-8 items-start">
            <aside className="space-y-4">
              <div className="glass-effect p-4 rounded-3xl">
                <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-[0.3em] mb-3 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-primary-500" />
                  策略案例
                </h3>
                <div className="space-y-3">
                  {loadingTemplates && (
                    <div className="w-full text-center py-6 text-sm text-slate-500">正在载入模板库…</div>
                  )}
                  {templatesError && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
                      {templatesError}
                    </div>
                  )}
                  {templateList.map((template) => {
                    const isActive = template.id === selectedTemplateId
                    const visual = TEMPLATE_VISUALS[template.template_type] ?? TEMPLATE_VISUALS.valuation
                    const Icon = visual.Icon
                    return (
                      <button
                        key={template.id}
                        onClick={() => setSelectedTemplateId(template.id)}
                        className={`w-full text-left p-4 rounded-2xl transition-all ${
                          isActive
                            ? 'bg-primary-500 text-white shadow-[0_18px_40px_rgba(42,199,165,0.25)]'
                            : 'bg-white/70 text-slate-700 hover:bg-white shadow-sm'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <span
                            className={`mt-0.5 w-10 h-10 shrink-0 rounded-2xl flex items-center justify-center bg-gradient-to-br ${visual.gradient}`}
                          >
                            <Icon className="w-5 h-5 text-white" />
                          </span>
                          <div className="flex-1">
                            <div className="flex items-center justify-between gap-2">
                              <div className="text-sm font-semibold">{template.title}</div>
                              <span
                                className={`text-[0.65rem] uppercase tracking-[0.35em] ${
                                  isActive ? 'text-white/70' : 'text-slate-400'
                                }`}
                              >
                                {visual.badge}
                              </span>
                            </div>
                            <div className={`mt-2 text-xs leading-relaxed ${isActive ? 'text-white/80' : 'text-slate-500'}`}>
                              {template.description}
                            </div>
                            {template.ticker && (
                              <div className={`mt-2 text-xs ${isActive ? 'text-white/70' : 'text-slate-400'}`}>
                                标的：{template.ticker}
                              </div>
                            )}
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            </aside>

            <main className="glass-effect-strong p-8 rounded-3xl space-y-8">
              {selectedTemplate ? (
                <>
                  <div className="space-y-3">
                    <h2 className="text-3xl font-bold text-slate-900 text-center">
                      {selectedTemplate.title}
                    </h2>
                    <p className="text-slate-600 text-center">
                      {selectedTemplate.template_type === 'custom'
                        ? '自由组合输入参数，生成个性化策略草稿'
                        : `以 ${selectedTemplate.ticker ?? '核心赛道'} 为例，快速生成投资策略报告`}
                    </p>
                  </div>

                  {selectedTemplate.template_type !== 'custom' && scenarioBadges.length > 0 && (
                    <div className="flex flex-wrap items-center justify-center gap-3">
                      {scenarioBadges.map((badge) => (
                        <div
                          key={`${badge.label}-${badge.value}`}
                          className="rounded-2xl bg-white/75 border border-white/60 px-4 py-2 shadow-sm"
                        >
                          <div className="text-[0.65rem] uppercase tracking-[0.3em] text-primary-500/70">
                            {badge.label}
                          </div>
                          <div className="text-sm font-semibold text-slate-800 whitespace-nowrap">
                            {badge.value}
                          </div>
                        </div>
                      ))}
                      {selectedTemplate.template_type === 'valuation' && computePeValue && (
                        <div className="rounded-2xl bg-white/75 border border-white/60 px-4 py-2 shadow-sm">
                          <div className="text-[0.65rem] uppercase tracking-[0.3em] text-primary-500/70">
                            实时估值
                          </div>
                          <div className="text-sm font-semibold text-slate-800 whitespace-nowrap">
                            当前 PE ≈ {computePeValue}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {selectedTemplate.analysis_focus && selectedTemplate.analysis_focus.length > 0 && (
                    <div className="rounded-2xl border border-white/60 bg-white/80 p-6">
                      <div className="text-sm font-semibold text-slate-800">策略看点</div>
                      <ul className="mt-3 space-y-2 text-sm text-slate-600">
                        {selectedTemplate.analysis_focus.map((item) => (
                          <li key={item} className="flex items-start gap-3">
                            <span className="mt-1 h-2.5 w-2.5 rounded-full bg-primary-400/70" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedTemplate.verification_sources && selectedTemplate.verification_sources.length > 0 && (
                    <div className="rounded-2xl border border-white/60 bg-white/70 p-6">
                      <div className="text-sm font-semibold text-slate-800">验证锚点</div>
                      <ul className="mt-3 space-y-2 text-sm text-slate-600">
                        {selectedTemplate.verification_sources.map((item) => (
                          <li key={item} className="flex items-start gap-3">
                            <span className="mt-1 h-2 w-2 rounded-full bg-slate-300" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {selectedTemplate.template_type !== 'custom' ? (
                    <div className="space-y-6">
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          目标标的 / 公司
                        </label>
                        <input
                          value={userTarget}
                          onChange={(e) => {
                            const value = e.target.value
                            setUserTarget(value)
                            if (selectedTemplate) {
                              const prev = templateMetaRef.current[selectedTemplate.id] ?? {
                                target: '',
                                focus: '',
                                notes: '',
                              }
                              templateMetaRef.current[selectedTemplate.id] = {
                                target: value,
                                focus: prev.focus,
                                notes: prev.notes,
                              }
                            }
                          }}
                          placeholder={selectedTemplate.ticker ?? '例如：300750.SZ 宁德时代'}
                          className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">
                          关注角度（可选）
                        </label>
                        <input
                          value={userFocus}
                          onChange={(e) => {
                            const value = e.target.value
                            setUserFocus(value)
                            if (selectedTemplate) {
                              const prev = templateMetaRef.current[selectedTemplate.id] ?? {
                                target: userTarget,
                                focus: '',
                                notes: '',
                              }
                              templateMetaRef.current[selectedTemplate.id] = {
                                target: prev.target ?? userTarget,
                                focus: value,
                                notes: prev.notes,
                              }
                            }
                          }}
                          placeholder="如：现金流修复、出海节奏、风险对冲"
                          className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {selectedTemplate.required_inputs.map((input) => (
                          <div key={input.field}>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                              {input.label}
                            </label>
                            {input.type === 'select' && input.options ? (
                              <select
                                value={inputValues[input.field] ?? ''}
                                onChange={(e) => handleInputChange(input.field, e.target.value)}
                                className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                              >
                                <option value="">请选择</option>
                                {input.options.map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                            ) : (
                              <input
                                type={input.type === 'number' ? 'number' : 'text'}
                                value={inputValues[input.field] ?? ''}
                                onChange={(e) => handleInputChange(input.field, e.target.value)}
                                placeholder={input.placeholder}
                                className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                              />
                            )}
                          </div>
                        ))}
                      </div>

                      {selectedTemplate.optional_inputs && selectedTemplate.optional_inputs.length > 0 && (
                        <div className="rounded-2xl border border-slate-200 bg-white/70 p-6 space-y-4">
                          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                            <BarChart3 className="w-4 h-4 text-teal-500" />
                            自定义假设（可选）
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {selectedTemplate.optional_inputs.map((input) => (
                              <div key={input.field}>
                                <label className="block text-sm font-medium text-slate-700 mb-2">
                                  {input.label}
                                </label>
                                {input.type === 'select' && input.options ? (
                                  <select
                                    value={inputValues[input.field] ?? ''}
                                    onChange={(e) => handleInputChange(input.field, e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                  >
                                    <option value="">可选</option>
                                    {input.options.map((option) => (
                                      <option key={option.value} value={option.value}>
                                        {option.label}
                                      </option>
                                    ))}
                                  </select>
                                ) : (
                                  <input
                                    type={input.type === 'number' ? 'number' : 'text'}
                                    value={inputValues[input.field] ?? ''}
                                    onChange={(e) => handleInputChange(input.field, e.target.value)}
                                    placeholder={input.placeholder}
                                    className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                  />
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-2">
                      想让 AI 聚焦的问题 / 备注
                    </label>
                    <textarea
                      value={userNotes}
                      onChange={(e) => {
                        const value = e.target.value
                        setUserNotes(value)
                        if (selectedTemplate) {
                          const prev = templateMetaRef.current[selectedTemplate.id] ?? {
                            target: userTarget,
                            focus: userFocus,
                            notes: '',
                          }
                          templateMetaRef.current[selectedTemplate.id] = {
                            target: prev.target ?? userTarget,
                            focus: prev.focus ?? userFocus,
                            notes: value,
                          }
                        }
                      }}
                      placeholder="例如：想验证估值区间、想让 AI 强调哪些风险、还有哪些后续问题…"
                      className="w-full h-24 px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none"
                    />
                  </div>

                  <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                    <button
                      onClick={handleGenerate}
                      disabled={isGenerating || loadingTemplates || !selectedTemplate}
                      className="flex items-center justify-center gap-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-slate-300 text-white font-semibold rounded-xl transition-colors w-full md:w-auto"
                    >
                      {isGenerating ? (
                        <>
                          <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          正在生成…
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-5 h-5" />
                          生成策略报告
                        </>
                      )}
                    </button>

                    <button
                      onClick={handleDownload}
                      className="flex items-center justify-center gap-2 px-6 py-3 border border-slate-300 text-slate-700 rounded-xl hover:bg-slate-50 transition-colors w-full md:w-auto"
                    >
                      <Download className="w-5 h-5" />
                      下载草稿文本
                    </button>
                  </div>

                  {errorMessage && (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
                      {errorMessage}
                    </div>
                  )}

                  <AnimatePresence mode="wait">
                    {apiResult && (
                      <motion.div
                        key={`report-${apiResult.report.slice(0, 12)}`}
                        initial={{ opacity: 0, y: 40 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -40 }}
                        className="rounded-2xl border border-blue-200 bg-blue-50 p-6 space-y-6"
                      >
                        <div className="flex items-center gap-3">
                          <CheckCircle className="w-6 h-6 text-blue-500" />
                          <h3 className="text-lg font-semibold text-slate-900">
                            {selectedTemplate.cta_label ?? '投研报告'}已生成
                          </h3>
                        </div>

                        <div className="rounded-2xl border border-white/60 bg-white/80 p-4 space-y-3 text-sm text-slate-700 leading-relaxed">
                          {finalReportParagraphs.map((para, idx) => (
                            <p key={idx} className="whitespace-pre-line">
                              {para}
                            </p>
                          ))}
                        </div>

                        {(dataAnalysisSegment || metadataSnapshot.dataAnalysis) && (
                          <div className="rounded-2xl border border-slate-200 bg-white/80 p-4 space-y-2">
                            <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                              <LineChart className="w-4 h-4 text-sky-500" />
                              数据分析摘要
                            </div>
                            {highlightText(metadataSnapshot.dataAnalysis?.analysis_preview || dataAnalysisSegment).map(
                              (item) => (
                                <p key={item} className="text-sm text-slate-700 whitespace-pre-line">
                                  {item}
                                </p>
                              )
                            )}
                            {metadataSnapshot.dataAnalysis?.highlights && metadataSnapshot.dataAnalysis.highlights.length > 0 && (
                              <ul className="text-sm text-slate-600 space-y-1">
                                {metadataSnapshot.dataAnalysis.highlights.map((item) => (
                                  <li key={item}>• {item}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}

                        {metadataSnapshot.strategy?.recommendation && (
                          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/80 p-4 space-y-3">
                            <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
                              <Sparkles className="w-4 h-4" />
                              最终投资建议
                            </div>
                            <div className="space-y-2">
                              <p className="text-sm text-emerald-900">
                                建议：{metadataSnapshot.strategy.recommendation}
                                {metadataSnapshot.strategy.target_price ? `｜目标价：${metadataSnapshot.strategy.target_price}` : ''}
                                {metadataSnapshot.strategy.confidence ? `｜置信度：${metadataSnapshot.strategy.confidence}` : ''}
                                {metadataSnapshot.strategy.position_suggestion ? `｜仓位：${metadataSnapshot.strategy.position_suggestion}` : ''}
                                {metadataSnapshot.strategy.time_horizon ? `｜周期：${metadataSnapshot.strategy.time_horizon}` : ''}
                              </p>
                              {metadataSnapshot.strategy.entry_conditions && Array.isArray(metadataSnapshot.strategy.entry_conditions) && metadataSnapshot.strategy.entry_conditions.length > 0 && (
                                <div className="text-xs text-emerald-800">
                                  <span className="font-medium">入场条件：</span>
                                  {metadataSnapshot.strategy.entry_conditions.slice(0, 3).join('；')}
                                  {metadataSnapshot.strategy.entry_conditions.length > 3 ? `等${metadataSnapshot.strategy.entry_conditions.length}项` : ''}
                                </div>
                              )}
                              {metadataSnapshot.strategy.exit_conditions && Array.isArray(metadataSnapshot.strategy.exit_conditions) && metadataSnapshot.strategy.exit_conditions.length > 0 && (
                                <div className="text-xs text-emerald-800">
                                  <span className="font-medium">出场条件：</span>
                                  {metadataSnapshot.strategy.exit_conditions.slice(0, 3).join('；')}
                                  {metadataSnapshot.strategy.exit_conditions.length > 3 ? `等${metadataSnapshot.strategy.exit_conditions.length}项` : ''}
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        <div className="flex flex-wrap gap-3 justify-center">
                          <button
                            onClick={() => navigate('/qa')}
                            className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors flex items-center gap-2"
                          >
                            <Sparkles className="w-4 h-4" />
                            继续与 AI 问答协同
                          </button>
                          <button
                            onClick={handleDownload}
                            className="px-6 py-3 border border-slate-300 text-slate-700 rounded-xl hover:bg-slate-50 transition-colors flex items-center gap-2"
                          >
                            <Download className="w-4 h-4" />
                            下载草稿文本
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </>
              ) : (
                <div className="h-48 flex items-center justify-center text-slate-500 text-sm">
                  请选择左侧模板开始
                </div>
              )}
            </main>

            <aside className="glass-effect-strong p-6 rounded-3xl space-y-4">
              <h3 className="text-lg font-semibold text-slate-900 text-center">生成流程</h3>
              <div className="space-y-3">
                {currentTimelineEvent ? (
                  <div className="bg-white/80 border border-white/70 rounded-2xl px-4 py-3 shadow-sm">
                    <div className="text-sm font-semibold text-slate-800">{currentTimelineEvent.title}</div>
                    {currentTimelineEvent.content && (
                      <div className="text-xs text-slate-600 mt-1 whitespace-pre-line leading-relaxed">
                        {timelineRenderedContent}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-white/70 border border-dashed border-slate-200 rounded-2xl px-4 py-3 text-sm text-slate-500">
                    投研生成的过程提示会在这里滚动显示。
                  </div>
                )}
              </div>

              {metadataSnapshot.dataAnalysis?.highlights && metadataSnapshot.dataAnalysis.highlights.length > 0 && (
                null
              )}

              {metadataSnapshot.strategy?.highlights && metadataSnapshot.strategy.highlights.length > 0 && (
                null
              )}
            </aside>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default ResearchLab
