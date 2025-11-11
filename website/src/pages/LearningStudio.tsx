import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Calculator,
  TrendingUp,
  CheckCircle,
  BookOpen,
  Target,
  Lightbulb,
  Plus,
  Trash2,
} from 'lucide-react'
import { fetchLearningTopics, runQuery, getWebSocketBase } from '../lib/apiClient'
import type {
  LearningTopic,
  LearningTopicKeyDataPoint,
  LearningWorkshopMetadata,
  QueryResponse,
} from '../types'

type CalculatorEntry = {
  id: string
  label: string
  unit?: string
  presetValue?: number
  userValue: string
  editable: boolean
}

type TimelineEvent = {
  id: string
  title: string
  content?: string
}

type StreamMessage =
  | { type: 'status'; message: string }
  | { type: 'timeline'; title: string; content?: string }
  | { type: 'final'; payload: QueryResponse }
  | { type: 'error'; message: string }

const TIMEWRITER_INTERVAL_MS = 24
const TIMELINE_SWITCH_DELAY_MS = 240

const FALLBACK_TOPICS: LearningTopic[] = [
  {
    id: 'blockchain_cbdc_fallback',
    title: '区块链支付 · CBDC 试点',
    knowledge_point: '区块链支付 / CBDC',
    category: ['支付科技', '央行数字货币'],
    key_data_points: [
      { label: '试点城市', value: '11 个重点城市', source: '中国人民银行数字货币研究所 2025Q1' },
      { label: '注册钱包用户', value: '超 1.1 亿', source: '央行 2025-04 公告' },
      { label: '累计交易笔数', value: '2.8 亿 · 1.3 万亿元', source: '上海 CBDC 试点办 2025Q1 报告' },
    ],
    learning_objectives: [
      '理解 CBDC 试点的目标、范围与关键指标',
      '掌握数字化收入增长率在场景分析中的应用',
      '能将试点数据映射到银行业务影响分析',
    ],
    difficulty: 'intermediate',
    estimated_time: '15 min',
    task: {
      prompt: '基于 CBDC 试点数据，评估银行数字化业务收入增长的驱动因素并给出验证逻辑。',
      calculator_inputs: [
        { label: '试点前数字化收入', value: 10, unit: '亿元' },
        { label: '试点后数字化收入', value: 12, unit: '亿元' },
      ],
      formula: '增长率 = (试点后收入 - 试点前收入) / 试点前收入',
      expected_result: '增长率约 20%，需结合渗透率与支付效率解释原因。',
      explanation: '关注支付结算周期缩短、钱包用户扩张以及增值服务收入贡献。',
    },
    validation: {
      reference_data: '2025Q1 财报显示数字化业务收入同比增长 19%-22%',
      insight: 'CBDC 缩短清算周期 30%，提升公对公快速支付效率，利于扩展增值服务。',
    },
    recommended_followups: ['分析 CBDC 对跨境支付业务的影响', '评估 CBDC 推动的客户留存变化'],
  },
  {
    id: 'domestic_ai_supply_chain',
    title: '国产 AI 服务器 · 供给链复盘',
    knowledge_point: 'AI 服务器 / 算力集群',
    category: ['人工智能', '硬件供给'],
    key_data_points: [
      { label: '季度出货量', value: '同比 +110%', source: '工信部算力发展白皮书 2025' },
      { label: '国产 GPU 占比', value: '45%', source: '信创硬件联盟 2025Q2' },
      { label: 'TOP10 金融机构覆盖率', value: '80%', source: '券商行业研究 2025Q2' },
    ],
    learning_objectives: [
      '评估国产算力替代对下游行业的影响',
      '掌握拆解设备出货量与项目交付节奏的方法',
      '构建芯片占比与算力供给的估算逻辑',
    ],
    difficulty: 'advanced',
    estimated_time: '25 min',
    task: {
      prompt: '拆解 AI 服务器出货量翻倍的驱动因素，并推算算力集群项目的增量收益。',
      calculator_inputs: [
        { label: '2024 出货量', value: 6, unit: '万台' },
        { label: '2025 出货量', value: 12, unit: '万台' },
        { label: '单台毛利', value: 8, unit: '万元' },
      ],
      formula: '增量毛利 = (2025 出货量 - 2024 出货量) × 单台毛利',
      expected_result: '增量毛利 ≈ 48 亿元，需验证产能与交付节奏是否匹配。',
      explanation: '聚焦 GPU 占比提升、订单锁定周期与交付节奏，判断增长可持续性。',
    },
    validation: {
      reference_data: '龙头厂商订单覆盖 9 个月产能，GPU 良率提升至 92%',
      insight: '需关注国产芯片供给弹性及海外项目交付风险。',
    },
    recommended_followups: ['追踪 GPU 良率与成本变动', '评估行业算力需求持续性与采购节奏'],
  },
  {
    id: 'global_ai_saas',
    title: 'Global AI SaaS Adoption',
    knowledge_point: 'Generative AI SaaS',
    category: ['SaaS', 'Generative AI'],
    key_data_points: [
      { label: '部署企业占比', value: 'Fortune 500 中 62%', source: 'McKinsey AI Survey 2025' },
      { label: '平均 ROI 周期', value: '13.5 个月', source: 'Gartner SaaS ROI Benchmark 2025' },
      { label: '成本节约', value: '业务单元平均 -18%', source: 'IDC GenAI Adoption 2025' },
    ],
    learning_objectives: [
      '理解生成式 AI 在企业级场景的价值链',
      '掌握评估 SaaS 项目 ROI 的关键变量',
      '构建跨行业效率提升指标体系',
    ],
    difficulty: 'intermediate',
    estimated_time: '20 min',
    task: {
      prompt: '评估一家全球制造企业部署 GenAI SaaS 后的 ROI，并提出推广建议。',
      calculator_inputs: [
        { label: 'SaaS 年费', value: 3.2, unit: '百万美元' },
        { label: '效率提升节约', value: 4.1, unit: '百万美元' },
        { label: '实施周期', value: 12, unit: '个月' },
      ],
      formula: 'ROI = (效率提升节约 - SaaS 年费) / SaaS 年费',
      expected_result: 'ROI ≈ 28%，需要结合部门适配度完善推广策略。',
      explanation: '验证数据安全、员工培训与跨地区部署差异，并制定持续优化路线图。',
    },
    validation: {
      reference_data: '案例企业 6 个月完成两部门上线，客服满意度提升 12%',
      insight: '推广节奏需结合本地法规与数据合规要求。',
    },
    recommended_followups: ['结合法规制定分阶段上线计划', '设计员工培训与流程改造 KPI 体系'],
  },
]

const formatKeyDataPoint = (point: LearningTopicKeyDataPoint): string => {
  const base = `${point.label}：${point.value}`
  return point.source ? `${base}（来源：${point.source}）` : base
}

const LearningStudio: React.FC = () => {
  const navigate = useNavigate()
  const [topics, setTopics] = useState<LearningTopic[]>([])
  const [loadingTopics, setLoadingTopics] = useState(true)
  const [topicsError, setTopicsError] = useState<string | null>(null)
  const [selectedTopicId, setSelectedTopicId] = useState<string>('')
  const [calculatorEntries, setCalculatorEntries] = useState<CalculatorEntry[]>([])
  const [customCalculatorEntries, setCustomCalculatorEntries] = useState<CalculatorEntry[]>([])
  const [learnerNotes, setLearnerNotes] = useState('')
  const [taskResult, setTaskResult] = useState<string | null>(null)
  const [metadata, setMetadata] = useState<LearningWorkshopMetadata | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [currentTimelineEvent, setCurrentTimelineEvent] = useState<TimelineEvent | null>(null)
  const [timelineRenderedContent, setTimelineRenderedContent] = useState('')
  const [isCalculating, setIsCalculating] = useState(false)
  const entryIdRef = useRef(0)
  const wsRef = useRef<WebSocket | null>(null)
  const typewriterRef = useRef<number | null>(null)
  const timelineQueueRef = useRef<TimelineEvent[]>([])
  const timelineProcessingRef = useRef(false)

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

  const processTimelineQueue = useCallback(() => {
    if (timelineProcessingRef.current) return
    const nextEvent = timelineQueueRef.current.shift()
    if (!nextEvent) return

    timelineProcessingRef.current = true
    setCurrentTimelineEvent(nextEvent)

    const content = nextEvent.content
    if (!content) {
      setTimelineRenderedContent('')
      typewriterRef.current = window.setTimeout(() => {
        typewriterRef.current = null
        timelineProcessingRef.current = false
        processTimelineQueue()
      }, TIMELINE_SWITCH_DELAY_MS)
      return
    }

    setTimelineRenderedContent('')

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
      timelineQueueRef.current.push({
        id: `${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
        title,
        content,
      })
      processTimelineQueue()
    },
    [processTimelineQueue]
  )

  const [customScenario, setCustomScenario] = useState({
    title: '自定义学习场景',
    knowledgePoint: '',
    scenarioSummary: '',
    learningObjectivesText: '',
    keyDataPointsText: '',
    taskPrompt: '',
    formula: '',
    expectedResult: '',
    validationReference: '',
    validationInsight: '',
    followupsText: '',
    difficulty: 'intermediate' as 'beginner' | 'intermediate' | 'advanced',
    estimatedTime: '20 min',
  })

  const createCustomEntry = (): CalculatorEntry => {
    const id = `custom-${entryIdRef.current++}`
    return {
      id,
      label: '',
      unit: '',
      userValue: '',
      editable: true,
    }
  }

  useEffect(() => {
    const loadTopics = async () => {
      try {
        const response = await fetchLearningTopics()
        setTopics(response.topics ?? [])
      } catch (error) {
        console.error('fetchLearningTopics error', error)
        setTopicsError(error instanceof Error ? error.message : '无法获取学习场景')
      } finally {
        setLoadingTopics(false)
      }
    }

    loadTopics()
  }, [])

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      stopTypewriter()
      timelineQueueRef.current = []
      timelineProcessingRef.current = false
    }
  }, [stopTypewriter])

  const mergedTopics = useMemo(() => {
    const uniqueById = new Map<string, LearningTopic>()
    const knowledgeSeen = new Set<string>()

    for (const topic of topics) {
      uniqueById.set(topic.id, topic)
      if (topic.knowledge_point) {
        knowledgeSeen.add(topic.knowledge_point)
      }
    }

    for (const topic of FALLBACK_TOPICS) {
      if (uniqueById.has(topic.id)) continue
      if (knowledgeSeen.has(topic.knowledge_point)) continue
      uniqueById.set(topic.id, topic)
    }

    return Array.from(uniqueById.values())
  }, [topics])

  useEffect(() => {
    if (!selectedTopicId && mergedTopics.length > 0) {
      const first = mergedTopics[0]
      setSelectedTopicId(first.id)
      const entries =
        first.task?.calculator_inputs?.map((input, index) => ({
          id: `${first.id}-${index}`,
          label: input.label,
          unit: input.unit,
          presetValue: typeof input.value === 'number' ? input.value : undefined,
          userValue: input.value !== undefined ? String(input.value) : '',
          editable: false,
        })) ?? []
      setCalculatorEntries(entries)
    }
  }, [mergedTopics, selectedTopicId])

  const displayedTopics = useMemo(() => mergedTopics.slice(0, 3), [mergedTopics])
  const isCustom = selectedTopicId === 'custom'

  const parsedCustomLearningObjectives = useMemo(
    () =>
      customScenario.learningObjectivesText
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean),
    [customScenario.learningObjectivesText]
  )

  const parsedCustomKeyDataPoints = useMemo(() => {
    return customScenario.keyDataPointsText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map<LearningTopicKeyDataPoint>((line) => {
        const separatorIndex = line.indexOf(':') >= 0 ? line.indexOf(':') : line.indexOf('：')
        if (separatorIndex === -1) {
          return { label: line, value: '' }
        }
        const label = line.slice(0, separatorIndex).trim()
        const value = line.slice(separatorIndex + 1).trim()
        return { label, value }
      })
      .filter((point) => point.label && point.value)
  }, [customScenario.keyDataPointsText])

  const parsedCustomFollowups = useMemo(
    () =>
      customScenario.followupsText
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean),
    [customScenario.followupsText]
  )

  const selectedTopic: LearningTopic | null = useMemo(() => {
    if (isCustom) {
      return {
        id: 'custom',
        title: customScenario.title || '自定义学习场景',
        knowledge_point: customScenario.knowledgePoint || customScenario.title || '自定义知识点',
        category: [],
        scenario_summary:
          customScenario.scenarioSummary || '请在自定义区域补充场景描述，AI 将根据输入拆解步骤。',
        key_data_points: parsedCustomKeyDataPoints,
        learning_objectives: parsedCustomLearningObjectives,
        difficulty: customScenario.difficulty,
        estimated_time: customScenario.estimatedTime,
        task: {
          prompt:
            customScenario.taskPrompt ||
            '根据学习者提供的输入拆解关键步骤，并给出验证逻辑与下一步建议。',
          calculator_inputs: calculatorEntries.map((entry) => ({
            label: entry.label || '输入项',
            unit: entry.unit,
            value:
              entry.presetValue !== undefined
                ? entry.presetValue
                : entry.userValue && !Number.isNaN(Number(entry.userValue))
                ? Number(entry.userValue)
                : undefined,
          })),
          formula: customScenario.formula || undefined,
          expected_result: customScenario.expectedResult || undefined,
          explanation: undefined,
        },
        validation:
          customScenario.validationReference || customScenario.validationInsight
            ? {
                reference_data: customScenario.validationReference || undefined,
                insight: customScenario.validationInsight || undefined,
              }
            : undefined,
        recommended_followups: parsedCustomFollowups,
      }
    }

    return mergedTopics.find((topic) => topic.id === selectedTopicId) ?? null
  }, [
    calculatorEntries,
    customScenario,
    isCustom,
    mergedTopics,
    parsedCustomFollowups,
    parsedCustomKeyDataPoints,
    parsedCustomLearningObjectives,
    selectedTopicId,
  ])

  const overviewText = useMemo(() => {
    if (!selectedTopic) {
      return '选择或自定义一个场景，AI 将展示关键数据与执行要点。'
    }
    const summary = selectedTopic.scenario_summary?.trim()
    if (summary) return summary
    if (selectedTopic.task?.prompt) return selectedTopic.task.prompt
    return '调整下方参数，AI 会基于任务提示输出学习步骤与验证逻辑。'
  }, [selectedTopic])

  const handleSelectTopic = (topicId: string) => {
    if (isCustom) {
      setCustomCalculatorEntries(calculatorEntries)
    }

    resetTimeline()

    setTaskResult(null)
    setMetadata(null)
    setErrorMessage(null)
    setLearnerNotes('')

    if (topicId === 'custom') {
      const entries = customCalculatorEntries.length
        ? customCalculatorEntries
        : [createCustomEntry(), createCustomEntry()]
      setCalculatorEntries(entries)
      if (!customScenario.learningObjectivesText) {
        setCustomScenario((prev) => ({
          ...prev,
          learningObjectivesText: '明确要解决的问题\n整理需要验证的数据',
        }))
      }
      setSelectedTopicId('custom')
      return
    }

    const topic = mergedTopics.find((item) => item.id === topicId)
    if (topic) {
      const entries =
        topic.task?.calculator_inputs?.map((input, index) => ({
          id: `${topic.id}-${index}`,
          label: input.label,
          unit: input.unit,
          presetValue: typeof input.value === 'number' ? input.value : undefined,
          userValue: input.value !== undefined ? String(input.value) : '',
          editable: false,
        })) ?? []
      setCalculatorEntries(entries)
    } else {
      setCalculatorEntries([])
    }
    setSelectedTopicId(topicId)
  }

  const updateCalculatorEntry = (entryId: string, field: 'label' | 'unit' | 'userValue', value: string) => {
    setCalculatorEntries((prev) =>
      prev.map((entry) =>
        entry.id === entryId
          ? {
              ...entry,
              [field]: value,
            }
          : entry
      )
    )
    if (isCustom) {
      setCustomCalculatorEntries((prev) =>
        prev.map((entry) =>
          entry.id === entryId
            ? {
                ...entry,
                [field]: value,
              }
            : entry
        )
      )
    }
  }

  const handleAddCustomEntry = () => {
    const newEntry = createCustomEntry()
    setCalculatorEntries((prev) => [...prev, newEntry])
    setCustomCalculatorEntries((prev) => [...prev, newEntry])
  }

  const handleRemoveCustomEntry = (entryId: string) => {
    setCalculatorEntries((prev) => prev.filter((entry) => entry.id !== entryId))
    setCustomCalculatorEntries((prev) => prev.filter((entry) => entry.id !== entryId))
  }

  const calculatorSummaryForPrompt = (topic: LearningTopic, entries: CalculatorEntry[]): string => {
    if (!entries.length) return '学习者暂未提供计算器输入。'
    const lines = entries.map((entry) => {
      const value = entry.userValue || (entry.presetValue !== undefined ? entry.presetValue : '（未提供）')
      const unit = entry.unit ? ` ${entry.unit}` : ''
      return `${entry.label || '输入项'}: ${value}${unit}`
    })
    if (topic.task?.formula) {
      lines.push(`引用公式：${topic.task.formula}`)
    }
    return lines.join('\n')
  }

  const buildLearningPrompt = (topic: LearningTopic, entries: CalculatorEntry[]): string => {
    const keyData = topic.key_data_points?.length
      ? topic.key_data_points.map(formatKeyDataPoint).join('\n')
      : '（未列出关键数据）'
    const objectives = topic.learning_objectives?.length
      ? topic.learning_objectives.map((obj, idx) => `${idx + 1}. ${obj}`).join('\n')
      : '（未指定学习目标）'
    const followups = topic.recommended_followups?.length
      ? topic.recommended_followups.map((item, idx) => `${idx + 1}. ${item}`).join('\n')
      : ''
    const scenarioSummary = topic.scenario_summary?.trim() || ''

    return [
      `学习场景ID：${topic.id}`,
      `知识点：${topic.knowledge_point}`,
      `场景简介：${scenarioSummary || '（未提供场景简介）'}`,
      `关键数据：\n${keyData}`,
      `学习目标：\n${objectives}`,
      topic.task?.prompt ? `任务提示：\n${topic.task.prompt}` : '',
      topic.task?.expected_result ? `预期结果参考：${topic.task.expected_result}` : '',
      topic.validation?.reference_data ? `验证参考：${topic.validation.reference_data}` : '',
      topic.validation?.insight ? `验证洞察：${topic.validation.insight}` : '',
      followups ? `推荐延伸：\n${followups}` : '',
      `学习者输入：\n${calculatorSummaryForPrompt(topic, entries)}`,
      learnerNotes.trim() ? `学习者备注：\n${learnerNotes.trim()}` : '学习者备注：无',
      '请输出符合 LearningWorkshopSchema 的 JSON，涵盖学习目标、任务步骤、关键数据引用、验证逻辑与 AI 指导。',
    ]
      .filter(Boolean)
      .join('\n\n')
  }

  const handleGenerate = async () => {
    if (!selectedTopic) return

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    resetTimeline()

    setIsCalculating(true)
    setTaskResult(null)
    setMetadata(null)
    setErrorMessage(null)

    pushTimelineEvent('准备任务', '正在整理学习场景与输入……')

    const prompt = buildLearningPrompt(selectedTopic, calculatorEntries)

    const calculatorContext = calculatorEntries
      .filter((entry) => (entry.label && entry.label.trim()) || entry.userValue.trim())
      .map((entry) => {
        const trimmedValue = entry.userValue.trim()
        const numeric = Number(trimmedValue)
        const hasNumeric = trimmedValue !== '' && Number.isFinite(numeric)
        return {
          label: entry.label || '输入项',
          unit: entry.unit,
          value: hasNumeric ? numeric : entry.presetValue,
          raw:
            trimmedValue !== ''
              ? trimmedValue
              : entry.presetValue !== undefined
              ? String(entry.presetValue)
              : '',
        }
      })

    const contextPayload = {
      ...(selectedTopic.id ? { scenario_id: selectedTopic.id } : {}),
      ...(calculatorContext.length ? { calculator_inputs: calculatorContext } : {}),
    }

    const httpPayload = {
      query: prompt,
      scenarioOverride: 'learning_workshop' as const,
      context: Object.keys(contextPayload).length ? contextPayload : undefined,
    }

    const wsPayload = {
      query: prompt,
      scenario_override: 'learning_workshop',
      context: contextPayload,
    }

    let finalReceived = false
    let fallbackTriggered = false

    const fallbackToHttp = async (reason?: string) => {
      if (fallbackTriggered || finalReceived) return
      fallbackTriggered = true
      if (reason) {
        pushTimelineEvent('模式切换', reason)
      }
      try {
        const response = await runQuery(httpPayload)
        setTaskResult(response.report.trim())
        const workshopMeta = (response.metadata?.learning_workshop ?? null) as LearningWorkshopMetadata | null
        setMetadata(workshopMeta)
        pushTimelineEvent('AI 报告已生成', 'HTTP 模式下完成分析。')
      } catch (error) {
        console.error('LearningStudio fallback error:', error)
        const message = error instanceof Error ? error.message : '请求失败，请稍后再试。'
        setErrorMessage(message)
        pushTimelineEvent('请求失败', message)
      } finally {
        setIsCalculating(false)
      }
    }

    try {
      const wsUrl = `${getWebSocketBase()}/api/query/stream`
      const socket = new WebSocket(wsUrl)
      wsRef.current = socket

      socket.onopen = () => {
        pushTimelineEvent('实时通道已建立', 'AI 正在生成学习指引…')
        socket.send(JSON.stringify(wsPayload))
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as StreamMessage
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
            const response = data.payload
            setTaskResult(response.report.trim())
            const workshopMeta = (response.metadata?.learning_workshop ?? null) as LearningWorkshopMetadata | null
            setMetadata(workshopMeta)
            pushTimelineEvent('AI 报告已生成', '学习指引已更新。')
            setIsCalculating(false)
            socket.close()
          } else if (data.type === 'error') {
            pushTimelineEvent('请求失败', data.message)
            setErrorMessage(data.message)
            setIsCalculating(false)
            socket.close()
          }
        } catch (parseError) {
          console.error('WebSocket parse error:', parseError)
        }
      }

      socket.onerror = () => {
        void fallbackToHttp('WebSocket 连接异常，已切换为普通请求。')
      }

      socket.onclose = () => {
        wsRef.current = null
        if (!finalReceived && !fallbackTriggered) {
          void fallbackToHttp()
        }
      }
    } catch (error) {
      console.error('WebSocket init error:', error)
      await fallbackToHttp('无法建立 WebSocket 连接，正在改用普通请求。')
    }
  }

  const renderKeyDataGrid = (points: LearningTopicKeyDataPoint[]) => {
    if (!points.length) {
      return (
        <div className="text-sm text-gray-500 bg-white/60 rounded-xl px-4 py-3">
          暂无关键数据，可先记录自己掌握的信息。
        </div>
      )
    }
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {points.map((point, index) => (
          <div key={`${point.label}-${index}`} className="bg-white/70 p-4 rounded-xl">
            <p className="text-sm font-semibold text-gray-800">{point.label}</p>
            <p className="text-sm text-gray-600 mt-1">{point.value}</p>
            {point.source && <p className="text-xs text-gray-400 mt-1">来源：{point.source}</p>}
          </div>
        ))}
      </div>
    )
  }

  const renderCalculatorEntries = () => {
    if (!calculatorEntries.length) {
      return <div className="text-sm text-gray-500">当前场景未提供默认输入项，可直接记录自己的分析结果。</div>
    }

    return (
      <div className="space-y-3">
        {calculatorEntries.map((entry) => (
          <div
            key={entry.id}
            className="flex flex-col md:flex-row md:items-end gap-3 bg-white/80 rounded-2xl border border-white/80 px-4 py-3"
          >
            <div className="flex-1">
              {entry.editable ? (
                <input
                  value={entry.label}
                  onChange={(event) => updateCalculatorEntry(entry.id, 'label', event.target.value)}
                  placeholder="输入项名称"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              ) : (
                <div className="text-sm font-semibold text-gray-800">{entry.label}</div>
              )}
              {entry.presetValue !== undefined && !entry.editable && (
                <div className="text-xs text-gray-500 mt-1">
                  预设值：{entry.presetValue}
                  {entry.unit ? ` ${entry.unit}` : ''}
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 md:w-48">
              {entry.editable && (
                <input
                  value={entry.unit ?? ''}
                  onChange={(event) => updateCalculatorEntry(entry.id, 'unit', event.target.value)}
                  placeholder="单位"
                  className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              )}
              <input
                value={entry.userValue}
                onChange={(event) => updateCalculatorEntry(entry.id, 'userValue', event.target.value)}
                placeholder="输入数值或说明"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              {entry.editable && calculatorEntries.length > 1 && (
                <button
                  type="button"
                  onClick={() => handleRemoveCustomEntry(entry.id)}
                  className="p-2 text-gray-400 hover:text-red-500 transition-colors"
                  aria-label="移除输入项"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    )
  }

  const renderCustomScenarioEditor = () => {
    if (!isCustom) return null

    return (
      <div className="mb-8 space-y-4 bg-white/60 border border-white/80 rounded-3xl p-6">
        <h3 className="text-lg font-semibold text-gray-800">自定义场景配置</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">场景标题</label>
            <input
              value={customScenario.title}
              onChange={(event) => setCustomScenario((prev) => ({ ...prev, title: event.target.value }))}
              placeholder="例如：国内新能源储能项目评估"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">知识点</label>
            <input
              value={customScenario.knowledgePoint}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, knowledgePoint: event.target.value }))
              }
              placeholder="关联的知识点或课程"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">难度</label>
            <select
              value={customScenario.difficulty}
              onChange={(event) =>
                setCustomScenario((prev) => ({
                  ...prev,
                  difficulty: event.target.value as 'beginner' | 'intermediate' | 'advanced',
                }))
              }
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">预估耗时</label>
            <input
              value={customScenario.estimatedTime}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, estimatedTime: event.target.value }))
              }
              placeholder="例如：25 min"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">场景简介</label>
          <textarea
            value={customScenario.scenarioSummary}
            onChange={(event) =>
              setCustomScenario((prev) => ({ ...prev, scenarioSummary: event.target.value }))
            }
            placeholder="描述场景背景、目标与数据来源…"
            className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
            rows={3}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">
              学习目标（每行一条）
            </label>
            <textarea
              value={customScenario.learningObjectivesText}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, learningObjectivesText: event.target.value }))
              }
              placeholder="示例：\n理解储能项目的收益结构\n掌握投资回报拆解方法"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none"
              rows={3}
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">
              关键数据点（每行“指标:数值”）
            </label>
            <textarea
              value={customScenario.keyDataPointsText}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, keyDataPointsText: event.target.value }))
              }
              placeholder="示例：\n累计装机容量: 3.1GW\n主力客户: 头部电网公司"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none"
              rows={3}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">任务提示</label>
            <textarea
              value={customScenario.taskPrompt}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, taskPrompt: event.target.value }))
              }
              placeholder="告诉 AI 你期待的任务，例如拆解收益、列出验证步骤等。"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none"
              rows={3}
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">
              验证参考 / 洞察
            </label>
            <textarea
              value={customScenario.validationReference}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, validationReference: event.target.value }))
              }
              placeholder="列出可对比的真实数据或行业结论"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none"
              rows={3}
            />
            <input
              value={customScenario.validationInsight}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, validationInsight: event.target.value }))
              }
              placeholder="补充验证洞察或质疑点（可选）"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">
              参考公式 / 预期结果
            </label>
            <input
              value={customScenario.formula}
              onChange={(event) => setCustomScenario((prev) => ({ ...prev, formula: event.target.value }))}
              placeholder="例如：收益率 = （收益-成本）/ 成本"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
            <input
              value={customScenario.expectedResult}
              onChange={(event) =>
                setCustomScenario((prev) => ({ ...prev, expectedResult: event.target.value }))
              }
              placeholder="预期结果提示（可选）"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-gray-500 uppercase tracking-[0.3em]">
              推荐跟进（每行一条，可选）
            </label>
            <textarea
              value={customScenario.followupsText}
              onChange={(event) => setCustomScenario((prev) => ({ ...prev, followupsText: event.target.value }))}
              placeholder="示例：\n关注政府补贴政策更新\n追踪原材料价格走势"
              className="mt-2 w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 resize-none"
              rows={3}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={handleAddCustomEntry}
          className="flex items-center gap-2 px-3 py-2 bg-primary-50 text-primary-600 rounded-lg hover:bg-primary-100 transition-colors"
        >
          <Plus className="w-4 h-4" />
          添加计算器输入项
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen w-full relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-cyan-50 noise-bg">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(42,199,165,0.05),transparent_50%)]" />
      </div>

      <div className="relative z-10 p-4 sm:p-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-600 hover:text-primary-600 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Home
        </button>
      </div>

      <div className="relative z-10 flex flex-col justify-center px-4 sm:px-6 lg:px-8 pb-16">
        <AnimatePresence mode="wait">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            className="w-full px-2 sm:px-4 lg:px-12 xl:px-20"
          >
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-800 mb-4">
                {selectedTopic ? selectedTopic.title : 'Scenario-Based Learning Studio'}
              </h2>
              <p className="text-gray-600 max-w-2xl mx-auto">
                选择左侧的学习案例或自定义场景，调整下方参数与备注，右侧的学习时间线会实时呈现 AI 拆解过程与指引。
              </p>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-[260px_minmax(0,1fr)_320px] gap-6 xl:gap-8 items-start">
              <div className="space-y-4">
                <div className="glass-effect p-4 rounded-3xl">
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-[0.3em] mb-3 flex items-center gap-2">
                    <Target className="w-4 h-4 text-primary-500" />
                    Scenario Tasks
                  </h3>
                  <div className="space-y-3">
                    {loadingTopics && !displayedTopics.length ? (
                      <div className="w-full text-center py-4 text-sm text-gray-500">正在加载学习场景…</div>
                    ) : (
                      displayedTopics.map((topic) => {
                        const isActive = topic.id === selectedTopicId
                        const difficulty = (topic.difficulty ?? 'intermediate').toUpperCase()
                        const estimatedTime = topic.estimated_time ?? '20 min'
                        return (
                          <button
                            key={topic.id}
                            onClick={() => handleSelectTopic(topic.id)}
                            className={`w-full text-left p-4 rounded-2xl transition-all ${
                              isActive
                                ? 'bg-primary-500 text-white shadow-[0_18px_40px_rgba(42,199,165,0.25)]'
                                : 'bg-white/70 text-gray-700 hover:bg-white shadow-sm'
                            }`}
                          >
                            <div className="flex items-center justify-between text-xs uppercase tracking-[0.25em] mb-2">
                              <span>{difficulty}</span>
                              <span>{estimatedTime}</span>
                            </div>
                            <div className="text-sm font-semibold">{topic.title}</div>
                            <div className={`mt-1 text-xs ${isActive ? 'text-white/80' : 'text-gray-500'}`}>
                              {topic.knowledge_point}
                            </div>
                          </button>
                        )
                      })
                    )}
                    <button
                      onClick={() => handleSelectTopic('custom')}
                      className={`w-full text-left p-4 rounded-2xl transition-all border ${
                        isCustom
                          ? 'bg-primary-50 border-primary-200 text-primary-700 shadow-[0_18px_40px_rgba(42,199,165,0.18)]'
                          : 'bg-white/70 border-dashed border-primary-200 text-gray-700 hover:bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs uppercase tracking-[0.25em] mb-2">
                        <span>CUSTOM</span>
                        <span>Flexible</span>
                      </div>
                      <div className="text-sm font-semibold">自定义学习场景</div>
                      <div className="mt-1 text-xs text-gray-500">
                        录入独有的知识点与数据，生成个性化的学习任务。
                      </div>
                    </button>
                  </div>
                </div>
              </div>

              <div className="glass-effect-strong p-8 rounded-3xl space-y-8">
                {topicsError && (
                  <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
                    {topicsError} · 已使用示例场景。
                  </div>
                )}

                {renderCustomScenarioEditor()}

                <section className="space-y-4">
                  <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                    <BookOpen className="w-5 h-5" />
                    Task Overview
                  </h3>
                  <p className="text-gray-700 leading-relaxed">{overviewText}</p>
                  {selectedTopic && renderKeyDataGrid(selectedTopic.key_data_points ?? [])}
                  {selectedTopic?.recommended_followups && selectedTopic.recommended_followups.length > 0 && (
                    <div className="rounded-2xl bg-white/70 border border-white/80 px-4 py-3 text-sm text-gray-600">
                      <div className="font-semibold text-gray-700 mb-2">Recommended Follow-ups</div>
                      <ul className="space-y-1">
                        {selectedTopic.recommended_followups.map((item, idx) => (
                          <li key={idx}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </section>

                <section className="space-y-4">
                  <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                    <Lightbulb className="w-5 h-5" />
                    Learning Objectives
                  </h3>
                  <ul className="space-y-2">
                    {(selectedTopic?.learning_objectives ?? []).length ? (
                      selectedTopic!.learning_objectives.map((objective, index) => (
                        <li key={`${objective}-${index}`} className="flex items-start gap-2">
                          <CheckCircle className="w-4 h-4 text-primary-500 mt-0.5 flex-shrink-0" />
                          <span className="text-gray-700">{objective}</span>
                        </li>
                      ))
                    ) : (
                      <li className="text-sm text-gray-500">暂无学习目标，请在自定义场景中补充信息。</li>
                    )}
                  </ul>
                </section>

                <section className="space-y-4">
                  <h3 className="text-xl font-semibold text-gray-800 flex items-center gap-2">
                    <Calculator className="w-5 h-5" />
                    Complete the Task
                  </h3>
                  <div className="bg-white/70 border border-white/80 rounded-2xl p-6 space-y-4">
                    {selectedTopic?.task?.prompt ? (
                      <p className="text-gray-700 leading-relaxed">{selectedTopic.task.prompt}</p>
                    ) : (
                      <p className="text-gray-500 leading-relaxed">
                        填写计算器输入项或补充备注，AI 会据此生成步骤与验证逻辑。
                      </p>
                    )}

                    {selectedTopic?.task?.formula && (
                      <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-sm text-blue-600">
                        引用公式：{selectedTopic.task.formula}
                      </div>
                    )}

                    {renderCalculatorEntries()}

                    {selectedTopic?.task?.expected_result && (
                      <div className="bg-white/60 border border-white/80 rounded-xl px-4 py-3 text-sm text-gray-600">
                        预期结果参考：{selectedTopic.task.expected_result}
                      </div>
                    )}

                    {selectedTopic?.validation && (
                      <div className="space-y-2 text-sm text-gray-600">
                        {selectedTopic.validation.reference_data && (
                          <p>验证参考：{selectedTopic.validation.reference_data}</p>
                        )}
                        {selectedTopic.validation.insight && (
                          <p>验证洞察：{selectedTopic.validation.insight}</p>
                        )}
                      </div>
                    )}
                  </div>

                  <textarea
                    value={learnerNotes}
                    onChange={(event) => setLearnerNotes(event.target.value)}
                    placeholder="记录你的思考、假设或想让 AI 关注的问题……"
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none h-32"
                  />

                  <button
                    onClick={handleGenerate}
                    disabled={isCalculating || !selectedTopic}
                    className="w-full px-6 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 text-white font-semibold rounded-xl transition-colors flex items-center gap-2 justify-center"
                  >
                    {isCalculating ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        正在生成...
                      </>
                    ) : (
                      <>
                        <Calculator className="w-5 h-5" />
                        Generate Analysis Report
                      </>
                    )}
                  </button>

                  {errorMessage && (
                    <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
                      {errorMessage}
                    </div>
                  )}

                  <AnimatePresence>
                    {taskResult && (
                      <motion.div
                        initial={{ opacity: 0, y: 50 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -50 }}
                        className="glass-effect border border-white/70 p-6 rounded-2xl"
                      >
                        <div className="flex items-center gap-3 mb-4">
                          <CheckCircle className="w-6 h-6 text-primary-500" />
                          <h3 className="text-lg font-semibold text-gray-800">Analysis Complete</h3>
                        </div>
                        <div className="whitespace-pre-line text-gray-700 leading-relaxed">{taskResult}</div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {taskResult && (
                    <div className="flex justify-center">
                      <button
                        onClick={() => navigate('/research')}
                        className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors flex items-center gap-2"
                      >
                        <TrendingUp className="w-4 h-4" />
                        Continue with Research Flow
                      </button>
                    </div>
                  )}
                </section>
              </div>

              <div className="glass-effect-strong p-6 rounded-3xl space-y-4">
                <h3 className="text-lg font-semibold text-gray-800 text-center">Learning Timeline</h3>
                <div className="space-y-3">
                  {currentTimelineEvent ? (
                    <div
                      key={currentTimelineEvent.id}
                      className="bg-white/80 border border-white/70 rounded-2xl px-4 py-3 shadow-sm"
                    >
                      <div className="text-sm font-semibold text-gray-800">{currentTimelineEvent.title}</div>
                      {currentTimelineEvent.content && (
                        <div className="text-xs text-gray-600 mt-1 whitespace-pre-line leading-relaxed">
                          {timelineRenderedContent}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="bg-white/70 border border-dashed border-gray-200 rounded-2xl px-4 py-3 text-sm text-gray-500">
                      生成指引后，这里会展示 AI 的关键提示与结果摘要。
                    </div>
                  )}
                </div>

                {metadata && (
                  <div className="mb-6 glass-effect border border-white/70 rounded-2xl p-6">
                    <h4 className="text-lg font-semibold text-gray-800 mb-3">AI 指导摘要</h4>
                    {metadata.knowledge_point && (
                      <p className="text-sm text-gray-700 mb-4">知识点：{metadata.knowledge_point}</p>
                    )}
                    {Array.isArray(metadata.learning_objectives) && metadata.learning_objectives.length > 0 && (
                      <div className="mb-4">
                        <div className="text-sm font-semibold text-gray-800">学习目标</div>
                        <ul className="mt-2 space-y-1 text-sm text-gray-700">
                          {metadata.learning_objectives.map((obj: string, idx: number) => (
                            <li key={idx}>• {obj}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {Array.isArray(metadata.task_steps) && metadata.task_steps.length > 0 && (
                      <div className="mb-4">
                        <div className="text-sm font-semibold text-gray-800">任务步骤</div>
                        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-gray-700">
                          {metadata.task_steps.map((step: string, idx: number) => (
                            <li key={idx}>{step}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                    {metadata.validation_logic && (
                      <p className="text-sm text-gray-700 mb-2">验证逻辑：{metadata.validation_logic}</p>
                    )}
                    {metadata.ai_guidance && (
                      <p className="text-sm text-gray-700 mb-2">AI 指导：{metadata.ai_guidance}</p>
                    )}
                    <p className="text-xs text-gray-400">详细步骤与验证逻辑见 AI 报告。</p>
                  </div>
                )}

                {metadata?.validation_logic && (
                  <div className="glass-effect border border-white/70 rounded-2xl px-4 py-3 text-sm text-blue-700">
                    <div className="font-semibold mb-1 text-blue-800">验证逻辑</div>
                    <p>{metadata.validation_logic}</p>
                  </div>
                )}

                {metadata?.ai_guidance && (
                  <div className="glass-effect border border-white/70 rounded-2xl px-4 py-3 text-sm text-emerald-700">
                    <div className="font-semibold mb-1 text-emerald-800">AI 下一步建议</div>
                    <p>{metadata.ai_guidance}</p>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}

export default LearningStudio