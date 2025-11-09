import React, { useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, TrendingUp, BarChart3, Download, CheckCircle, Target } from 'lucide-react'
import { runQuery } from '../lib/apiClient'
import type { QueryResponse } from '../types'

const TEMPLATE_OPTIONS = [
  {
    id: 'valuation',
    name: 'Company Valuation Report',
    description: 'Company valuation analysis based on financial data and market comparison',
    icon: TrendingUp,
    color: 'from-blue-500 to-blue-600'
  },
  {
    id: 'industry',
    name: 'Industry Analysis Report',
    description: 'Industry trends, competitive landscape, and development prospects analysis',
    icon: BarChart3,
    color: 'from-green-500 to-green-600'
  },
  {
    id: 'risk',
    name: 'Risk Assessment Report',
    description: 'Investment risk identification, quantification, and management recommendations',
    icon: Target,
    color: 'from-orange-500 to-orange-600'
  }
]

const ResearchLab: React.FC = () => {
  const navigate = useNavigate()
  const [selectedTemplate, setSelectedTemplate] = useState<string>(TEMPLATE_OPTIONS[0].id)
  const [formData, setFormData] = useState({
    stockPrice: '200',
    eps: '10',
    industryPE: '15',
    company: 'TSLA'
  })
  const [showReport, setShowReport] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [apiResult, setApiResult] = useState<QueryResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const buildFallbackReport = () => {
    const stockPrice = parseFloat(formData.stockPrice)
    const eps = parseFloat(formData.eps)
    const industryPEValue = parseFloat(formData.industryPE)
    const currentPeValue = Number.isFinite(stockPrice / eps) ? (stockPrice / eps).toFixed(1) : '0.0'
    const recommendationFallback = Number.isFinite(stockPrice / eps) && stockPrice / eps > industryPEValue * 1.2 ? 'Cautious' : 'Recommended'

    return [
      `# ${formData.company} Valuation Analysis Report`,
      '',
      '## Executive Summary',
      `- Current Stock Price: $${formData.stockPrice}`,
      `- Earnings Per Share (EPS): $${formData.eps}`,
      `- Price-to-Earnings Ratio (PE): ${currentPeValue}`,
      `- Industry Average PE: ${formData.industryPE}`,
      '',
      '## Financial Analysis',
      `Current PE is ${currentPeValue}, ${Number(currentPeValue) > industryPEValue ? 'above' : 'below'} industry average of ${formData.industryPE}.`,
      '',
      '## Investment Recommendation',
      recommendationFallback,
      '',
      `---`,
      `*Data Source: Sina Finance, ${new Date().toLocaleDateString()}*`,
    ].join('\n')
  }

  const activeTemplate = useMemo(
    () => TEMPLATE_OPTIONS.find((tpl) => tpl.id === selectedTemplate) ?? TEMPLATE_OPTIONS[0],
    [selectedTemplate]
  )

  const handleGenerateReport = async () => {
    setIsGenerating(true)
    setShowReport(false)
    setApiResult(null)
    setErrorMessage(null)

    const prompt = [
      `投研模板: ${activeTemplate.name}`,
      `模板描述: ${activeTemplate.description}`,
      `核心参数: 公司=${formData.company}, 股价=${formData.stockPrice}, EPS=${formData.eps}, 行业PE=${formData.industryPE}`,
      '请按照投研实验室的结构生成完整的分析草稿，包含数据计算、要点总结与下一步建议。',
    ].join('\n')

    try {
      const response: QueryResponse = await runQuery({
        query: prompt,
        scenarioOverride: 'research_lab',
      })
      setApiResult(response)
      setShowReport(true)
    } catch (error) {
      console.error('ResearchLab API error:', error)
      setErrorMessage(error instanceof Error ? error.message : '请求失败')
      setShowReport(true)
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownload = () => {
    const reportContent = apiResult?.report ?? buildFallbackReport()

    const blob = new Blob([reportContent], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${formData.company}_valuation_report.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const stockPriceNum = parseFloat(formData.stockPrice) || 0
  const epsNum = parseFloat(formData.eps) || 0
  const industryPeNum = parseFloat(formData.industryPE) || 0
  const strategySegment = (apiResult?.segments?.strategy as Record<string, any>) ?? null
  const dataAnalysisSegment = apiResult?.segments?.data_analysis as string | undefined

  return (
    <div className="min-h-screen w-full relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-green-50 via-white to-blue-50 noise-bg">
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

      <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-5xl mx-auto w-full"
        >
          <div className="text-center mb-12">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-display font-bold text-gray-800 mb-4">
              End-to-End Research Lab
            </h1>
            <p className="text-lg sm:text-xl text-gray-600">
              Generate data-driven investment reports with structured templates and real-time data
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-8 items-start">
            <div className="space-y-4">
              <div className="glass-effect p-4 rounded-3xl">
                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-[0.3em] mb-3 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary-500" />
                  Templates
                </h3>
                <div className="space-y-3">
                  {TEMPLATE_OPTIONS.map((template) => {
                    const isActive = template.id === selectedTemplate
                    const Icon = template.icon
                    return (
                      <button
                        key={template.id}
                        onClick={() => {
                          setSelectedTemplate(template.id)
                          setShowReport(false)
                          setApiResult(null)
                          setErrorMessage(null)
                        }}
                        className={`w-full text-left p-4 rounded-2xl transition-all ${
                          isActive
                            ? 'bg-primary-500 text-white shadow-[0_18px_40px_rgba(42,199,165,0.25)]'
                            : 'bg-white/70 text-gray-700 hover:bg-white shadow-sm'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          <span
                            className={`w-10 h-10 rounded-2xl flex items-center justify-center bg-gradient-to-br ${template.color}`}
                          >
                            <Icon className="w-5 h-5 text-white" />
                          </span>
                          <div>
                            <div className="text-sm font-semibold">{template.name}</div>
                            <div className={`mt-1 text-xs ${isActive ? 'text-white/80' : 'text-gray-500'}`}>
                              {template.description}
                            </div>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>

            <div className="glass-effect-strong p-8 rounded-3xl">
              <div className="text-center mb-10">
                <h2 className="text-3xl font-bold text-gray-800 mb-3">
                  Generate {activeTemplate.name}
                </h2>
                <p className="text-gray-600">
                  Complete 2025 Tesla Valuation Analysis Report
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Company Symbol
                  </label>
                  <select
                    value={formData.company}
                    onChange={(e) => setFormData({ ...formData, company: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  >
                    <option value="TSLA">TSLA - Tesla</option>
                    <option value="AAPL">AAPL - Apple</option>
                    <option value="MSFT">MSFT - Microsoft</option>
                    <option value="GOOGL">GOOGL - Google</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Current Stock Price (USD)
                  </label>
                  <input
                    type="number"
                    value={formData.stockPrice}
                    onChange={(e) => setFormData({ ...formData, stockPrice: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Earnings Per Share (EPS)
                  </label>
                  <input
                    type="number"
                    value={formData.eps}
                    onChange={(e) => setFormData({ ...formData, eps: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Industry Average PE
                  </label>
                  <input
                    type="number"
                    value={formData.industryPE}
                    onChange={(e) => setFormData({ ...formData, industryPE: e.target.value })}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  />
                </div>
              </div>

              <div className="bg-white/60 p-6 rounded-2xl mb-8">
                <h3 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
                  <FileText className="w-5 h-5" />
                  Automatic Parameter Filling
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-700 leading-relaxed">
                  <div className="bg-blue-50 p-4 rounded-xl">
                    <p className="font-semibold text-blue-600 mb-2">Auto-Fetch Parameters</p>
                    <ul className="space-y-2">
                      <li>• Stock Price: ${formData.stockPrice}</li>
                      <li>• EPS: ${formData.eps}</li>
                      <li>• Industry PE: {formData.industryPE}</li>
                    </ul>
                  </div>
                  <div className="bg-green-50 p-4 rounded-xl">
                    <p className="font-semibold text-green-600 mb-2">Custom Assumptions</p>
                    <ul className="space-y-2">
                      <li>• Growth Expectation: 25%</li>
                      <li>• Margin Outlook: 18%</li>
                      <li>• Risk Premium: 4.5%</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="flex flex-col md:flex-row items-center justify-between gap-4 mb-8">
                <button
                  onClick={handleGenerateReport}
                  disabled={isGenerating}
                  className="flex items-center justify-center gap-2 px-6 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 text-white font-semibold rounded-xl transition-colors w-full md:w-auto"
                >
                  {isGenerating ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <FileText className="w-5 h-5" />
                      Generate Draft Report
                    </>
                  )}
                </button>

                <button
                  onClick={handleDownload}
                  className="flex items-center justify-center gap-2 px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors w-full md:w-auto"
                >
                  <Download className="w-5 h-5" />
                  Download Markdown
                </button>
              </div>

              {errorMessage && (
                <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
                  {errorMessage} · 已使用示例数据作为回退。
                </div>
              )}
 
              <AnimatePresence>
                {showReport && (
                  <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -40 }}
                    className="bg-blue-50 border border-blue-200 p-6 rounded-2xl"
                  >
                    <div className="flex items-center gap-3 mb-4">
                      <CheckCircle className="w-6 h-6 text-blue-500" />
                      <h3 className="text-lg font-semibold text-gray-800">Draft Report Ready</h3>
                    </div>

                    <div className="space-y-6">
                      <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                        {(apiResult?.report ?? buildFallbackReport()).trim()}
                      </div>

                      {dataAnalysisSegment && (
                        <div className="rounded-2xl border border-blue-200 bg-white/70 p-4">
                          <h4 className="text-sm font-semibold text-blue-700 mb-2">Data Analysis Summary</h4>
                          <p className="text-sm text-gray-700 whitespace-pre-line">{String(dataAnalysisSegment)}</p>
                        </div>
                      )}

                      {strategySegment && Object.keys(strategySegment).length > 0 && (
                        <div className="rounded-2xl border border-blue-200 bg-white/70 p-4">
                          <h4 className="text-sm font-semibold text-blue-700 mb-2">Strategy Highlights</h4>
                          <ul className="space-y-1 text-sm text-gray-700">
                            {Object.entries(strategySegment).map(([key, value]) => (
                              <li key={key}>
                                <span className="font-semibold text-gray-800 mr-2">{key}:</span>
                                <span>{typeof value === 'string' ? value : JSON.stringify(value)}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {showReport && (
                <div className="mt-8 flex justify-center gap-4">
                  <button
                    onClick={() => navigate('/qa')}
                    className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors flex items-center gap-2"
                  >
                    Continue with AI Q&A
                  </button>
                  <button
                    onClick={handleDownload}
                    className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors flex items-center gap-2"
                  >
                    <Download className="w-4 h-4" />
                    Download Markdown
                  </button>
                </div>
              )}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default ResearchLab