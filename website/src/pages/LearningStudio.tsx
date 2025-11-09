import React, { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Calculator, TrendingUp, CheckCircle, BookOpen, Target, Lightbulb } from 'lucide-react'
import { runQuery } from '../lib/apiClient'
import type { QueryResponse } from '../types'

interface Task {
  id: string
  title: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimatedTime: string
  scenario: string
  dataPoints: string[]
  learningObjectives: string[]
}

const TASKS: Task[] = [
  {
    id: 'cbdc-analysis',
    title: 'CBDC Impact Analysis',
    description: 'Calculate the growth rate of bank digitalization revenue after CBDC pilot implementation',
    difficulty: 'intermediate',
    estimatedTime: '15 min',
    scenario: '2025 China CBDC Pilot Program',
    dataPoints: ['Cities: 15 major cities', 'User Scale: 50M users', 'Transaction Volume: 2.3B transactions'],
    learningObjectives: [
      'Understand the impact of CBDC on traditional banking',
      'Master revenue growth rate calculation methods',
      'Learn to analyze the efficiency improvement of digital payments'
    ]
  },
  {
    id: 'tesla-valuation',
    title: 'Tesla Valuation Model',
    description: 'Build a DCF model to evaluate Tesla\'s reasonable valuation range',
    difficulty: 'advanced',
    estimatedTime: '30 min',
    scenario: '2025 Tesla Stock Analysis',
    dataPoints: ['Current Price: $200', 'EPS: $10', 'Expected Growth: 25%'],
    learningObjectives: [
      'Master DCF valuation model principles',
      'Learn to set reasonable growth assumptions',
      'Understand the relationship between growth and valuation'
    ]
  },
  {
    id: 'portfolio-optimization',
    title: 'Portfolio Optimization',
    description: 'Use Markowitz theory to optimize investment portfolio allocation',
    difficulty: 'beginner',
    estimatedTime: '20 min',
    scenario: 'Multi-asset Portfolio Construction',
    dataPoints: ['Assets: 5 major categories', 'Historical Data: 3 years', 'Risk Level: Medium'],
    learningObjectives: [
      'Understand the basic principles of modern portfolio theory',
      'Learn to calculate the efficient frontier',
      'Master risk-return trade-off analysis'
    ]
  }
]

const getMockResult = (taskId: string) => {
  if (taskId === 'cbdc-analysis') {
    const revenueBefore = 1000
    const revenueAfter = 1200
    const growthRate = ((revenueAfter - revenueBefore) / revenueBefore * 100).toFixed(1)
    return `Analysis Results:\n\nRevenue Growth Rate: +${growthRate}%\nBefore Revenue: $${revenueBefore}B\nAfter Revenue: $${revenueAfter}B\n\nConclusion: CBDC implementation significantly improves payment efficiency, driving digital revenue growth for banks.`
  }
  if (taskId === 'tesla-valuation') {
    const pe = 20
    const growth = 25
    const peg = (pe / growth).toFixed(2)
    const fairValue = parseFloat(peg) < 1 ? 'Undervalued' : parseFloat(peg) > 1.5 ? 'Overvalued' : 'Fair Value'
    return `Valuation Analysis:\n\nCurrent PE: ${pe}\nGrowth Rate: ${growth}%\nPEG Ratio: ${peg}\n\nValuation Status: ${fairValue}\nInvestment Recommendation: ${parseFloat(peg) < 1 ? 'Buy' : parseFloat(peg) > 1.5 ? 'Hold' : 'Hold'}`
  }
  if (taskId === 'portfolio-optimization') {
    const expectedReturn = 12.5
    const risk = 8.2
    const sharpeRatio = (expectedReturn / risk).toFixed(2)
    return `Portfolio Optimization Results:\n\nExpected Return: ${expectedReturn}%\nPortfolio Risk: ${risk}%\nSharpe Ratio: ${sharpeRatio}\n\nOptimization Effect: Risk-adjusted return improved by 15% compared to equal-weight allocation.`
  }
  return 'Mock data unavailable for the selected task.'
}

const LearningStudio: React.FC = () => {
  const navigate = useNavigate()
  const [activeTaskId, setActiveTaskId] = useState<string>(TASKS[0].id)
  const [taskInput, setTaskInput] = useState('')
  const [taskResult, setTaskResult] = useState<string | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)
  const [apiMetadata, setApiMetadata] = useState<Record<string, any> | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const selectedTask = useMemo(() => TASKS.find(task => task.id === activeTaskId) ?? TASKS[0], [activeTaskId])

  const handleCalculate = async () => {
    if (!taskInput.trim()) return
    setIsCalculating(true)
    setTaskResult(null)
    setApiMetadata(null)
    setErrorMessage(null)

    const prompt = [
      `场景化学习任务: ${selectedTask.title}`,
      `任务描述: ${selectedTask.description}`,
      `核心数据点: ${selectedTask.dataPoints.join('；')}`,
      `学习者反馈: ${taskInput}`,
      '请按照 LearningWorkshopSchema 的结构生成指导，并包含可执行步骤与验证逻辑。',
    ].join('\n')

    try {
      const response: QueryResponse = await runQuery({
        query: prompt,
        scenarioOverride: 'learning_workshop',
      })
      setTaskResult(response.report.trim())
      setApiMetadata(response.metadata ?? null)
    } catch (error) {
      console.error('LearningStudio API error:', error)
      setErrorMessage(error instanceof Error ? error.message : '请求失败')
      setTaskResult(getMockResult(selectedTask.id))
    } finally {
      setIsCalculating(false)
    }
  }

  return (
    <div className="min-h-screen w-full relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-cyan-50 noise-bg">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(42,199,165,0.05),transparent_50%)]" />
      </div>

      {/* Header */}
      <div className="relative z-10 p-4 sm:p-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-600 hover:text-primary-600 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          Back to Home
        </button>
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 sm:px-6 lg:px-8">
        <AnimatePresence mode="wait">
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            className="max-w-5xl mx-auto w-full"
          >
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-800 mb-4">Scenario-Based Learning Studio</h2>
              <p className="text-gray-600">Transform abstract knowledge into actionable tasks through real-world scenarios</p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-8 items-start">
              <div className="space-y-4">
                <div className="glass-effect p-4 rounded-3xl">
                  <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-[0.3em] mb-3 flex items-center gap-2">
                    <Target className="w-4 h-4 text-primary-500" />
                    Scenario Tasks
                  </h3>
                  <div className="space-y-3">
                    {TASKS.map((task) => {
                      const isActive = task.id === activeTaskId
                      return (
                        <button
                          key={task.id}
                          onClick={() => {
                            setActiveTaskId(task.id)
                            setTaskInput('')
                            setTaskResult(null)
                            setApiMetadata(null)
                            setErrorMessage(null)
                          }}
                          className={`w-full text-left p-4 rounded-2xl transition-all ${
                            isActive
                              ? 'bg-primary-500 text-white shadow-[0_18px_40px_rgba(42,199,165,0.25)]'
                              : 'bg-white/70 text-gray-700 hover:bg-white shadow-sm'
                          }`}
                        >
                          <div className="flex items-center justify-between text-xs uppercase tracking-[0.25em] mb-2">
                            <span>{task.difficulty.toUpperCase()}</span>
                            <span>{task.estimatedTime}</span>
                          </div>
                          <div className="text-sm font-semibold">{task.title}</div>
                          <div className={`mt-1 text-xs ${isActive ? 'text-white/80' : 'text-gray-500'}`}>
                            {task.scenario}
                          </div>
                        </button>
                      )
                    })}
                  </div>
                </div>
              </div>

              <div className="glass-effect-strong p-8 rounded-3xl">
                <div className="text-center mb-10">
                  <h2 className="text-3xl font-bold text-gray-800 mb-3">{selectedTask.title}</h2>
                  <p className="text-gray-600">{selectedTask.scenario}</p>
                </div>

                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <BookOpen className="w-5 h-5" />
                    Task Overview
                  </h3>
                  <p className="text-gray-700 mb-6">{selectedTask.description}</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    {selectedTask.dataPoints.map((point, index) => (
                      <div key={index} className="bg-white/70 p-4 rounded-xl">
                        <p className="text-sm text-gray-600">{point}</p>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <Lightbulb className="w-5 h-5" />
                    Learning Objectives
                  </h3>
                  <ul className="space-y-2">
                    {selectedTask.learningObjectives.map((objective, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                        <span className="text-gray-700">{objective}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <Calculator className="w-5 h-5" />
                    Complete the Task
                  </h3>
                  
                  <div className="bg-white/70 p-6 rounded-2xl mb-4">
                    {selectedTask.id === 'cbdc-analysis' && (
                      <div>
                        <p className="text-gray-700 mb-4">
                          Based on the 2025 CBDC pilot data, calculate the growth rate of bank digitalization revenue:
                        </p>
                        <div className="grid grid-cols-2 gap-4 mb-4">
                          <div className="bg-blue-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Revenue Before Pilot</p>
                            <p className="text-2xl font-bold text-blue-600">$10B</p>
                          </div>
                          <div className="bg-green-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Revenue After Pilot</p>
                            <p className="text-2xl font-bold text-green-600">$12B</p>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {selectedTask.id === 'tesla-valuation' && (
                      <div>
                        <p className="text-gray-700 mb-4">
                          Based on Tesla's current financial data, calculate key valuation metrics:
                        </p>
                        <div className="grid grid-cols-3 gap-4 mb-4">
                          <div className="bg-blue-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Stock Price</p>
                            <p className="text-2xl font-bold text-blue-600">$200</p>
                          </div>
                          <div className="bg-green-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">EPS</p>
                            <p className="text-2xl font-bold text-green-600">$10</p>
                          </div>
                          <div className="bg-purple-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Expected Growth</p>
                            <p className="text-2xl font-bold text-purple-600">25%</p>
                          </div>
                        </div>
                      </div>
                    )}
                    
                    {selectedTask.id === 'portfolio-optimization' && (
                      <div>
                        <p className="text-gray-700 mb-4">
                          Based on the given asset data, optimize portfolio allocation:
                        </p>
                        <div className="grid grid-cols-3 gap-4 mb-4">
                          <div className="bg-blue-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Expected Return</p>
                            <p className="text-2xl font-bold text-blue-600">12.5%</p>
                          </div>
                          <div className="bg-green-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Portfolio Risk</p>
                            <p className="text-2xl font-bold text-green-600">8.2%</p>
                          </div>
                          <div className="bg-purple-50 p-4 rounded-lg">
                            <p className="text-sm text-gray-600">Sharpe Ratio</p>
                            <p className="text-2xl font-bold text-purple-600">1.52</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                  
                  <textarea
                    value={taskInput}
                    onChange={(e) => setTaskInput(e.target.value)}
                    placeholder="Enter your analysis process and results..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none h-32 mb-4"
                  />
                  
                  <button
                    onClick={handleCalculate}
                    disabled={isCalculating}
                    className="w-full px-6 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
                  >
                    {isCalculating ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Analyzing...
                      </>
                    ) : (
                      <>
                        <Calculator className="w-5 h-5" />
                        Generate Analysis Report
                      </>
                    )}
                  </button>
                </div>

                {errorMessage && (
                  <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-600">
                    {errorMessage} · 已回退到示例数据。
                  </div>
                )}

                {apiMetadata?.learning_workshop && (
                  <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50/70 p-6">
                    <h4 className="text-lg font-semibold text-emerald-700 mb-3">AI 指导摘要</h4>
                    <p className="text-sm text-emerald-900 mb-4">
                      知识点：{apiMetadata.learning_workshop.knowledge_point}
                    </p>
                    {Array.isArray(apiMetadata.learning_workshop.learning_objectives) && (
                      <div className="mb-4">
                        <div className="text-sm font-semibold text-emerald-700">学习目标</div>
                        <ul className="mt-2 space-y-1 text-sm text-emerald-900">
                          {apiMetadata.learning_workshop.learning_objectives.map((obj: string, idx: number) => (
                            <li key={idx}>• {obj}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {Array.isArray(apiMetadata.learning_workshop.task_steps) && (
                      <div>
                        <div className="text-sm font-semibold text-emerald-700">任务步骤</div>
                        <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm text-emerald-900">
                          {apiMetadata.learning_workshop.task_steps.map((step: string, idx: number) => (
                            <li key={idx}>{step}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                )}

                <AnimatePresence>
                  {taskResult && (
                    <motion.div
                      initial={{ opacity: 0, y: 50 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -50 }}
                      className="bg-green-50 border border-green-200 p-6 rounded-2xl"
                    >
                      <div className="flex items-center gap-3 mb-4">
                        <CheckCircle className="w-6 h-6 text-green-500" />
                        <h3 className="text-lg font-semibold text-gray-800">Analysis Complete</h3>
                      </div>
                      <div className="whitespace-pre-line text-gray-700 leading-relaxed">
                        {taskResult}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {taskResult && (
                  <div className="mt-8 flex justify-center">
                    <button
                      onClick={() => navigate('/research')}
                      className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors flex items-center gap-2"
                    >
                      <TrendingUp className="w-4 h-4" />
                      Continue with Research Flow
                    </button>
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