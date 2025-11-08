import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, TrendingUp, BarChart3, Download, CheckCircle, Target } from 'lucide-react'

const ResearchLab: React.FC = () => {
  const navigate = useNavigate()
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    stockPrice: '200',
    eps: '10',
    industryPE: '15',
    company: 'TSLA'
  })
  const [showReport, setShowReport] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  const templates = [
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

  const handleGenerateReport = () => {
    setIsGenerating(true)
    setTimeout(() => {
      setIsGenerating(false)
      setShowReport(true)
    }, 2000)
  }

  const handleDownload = () => {
    const reportContent = `
# ${formData.company} Valuation Analysis Report

## Executive Summary
- Current Stock Price: $${formData.stockPrice}
- Earnings Per Share (EPS): $${formData.eps}
- Price-to-Earnings Ratio (PE): ${(parseFloat(formData.stockPrice) / parseFloat(formData.eps)).toFixed(1)}
- Industry Average PE: ${formData.industryPE}

## Financial Analysis
Current PE is ${(parseFloat(formData.stockPrice) / parseFloat(formData.eps)).toFixed(1)}, ${parseFloat(formData.stockPrice) / parseFloat(formData.eps) > parseFloat(formData.industryPE) ? 'above' : 'below'} industry average of ${formData.industryPE}.

## Investment Recommendation
${parseFloat(formData.stockPrice) / parseFloat(formData.eps) > parseFloat(formData.industryPE) * 1.2 ? 'Cautious' : 'Recommended'}

---
*Data Source: Sina Finance, ${new Date().toLocaleDateString()}*
`
    
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

  const currentPE = (parseFloat(formData.stockPrice) / parseFloat(formData.eps)).toFixed(1)
  const isAboveIndustry = parseFloat(currentPE) > parseFloat(formData.industryPE)
  const recommendation = isAboveIndustry ? 'Hold' : 'Buy'

  return (
    <div className="min-h-screen w-full relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-green-50 via-white to-blue-50 noise-bg">
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
          {!selectedTemplate && (
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -30 }}
              className="max-w-4xl mx-auto text-center"
            >
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-3xl sm:text-4xl lg:text-5xl font-display font-bold text-gray-800 mb-3 sm:mb-4"
              >
                End-to-End Research Lab
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-lg sm:text-xl text-gray-600 mb-8 sm:mb-12"
              >
                Generate data-driven investment reports with structured templates and real-time data
              </motion.p>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="text-lg text-primary-600 mb-16 font-medium"
              >
                "Research without the friction."
              </motion.p>

              {/* Template Selection */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-8 sm:mb-12">
                {templates.map((template, index) => (
                  <motion.div
                    key={template.id}
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 + index * 0.2 }}
                    className="group cursor-pointer"
                    onClick={() => setSelectedTemplate(template.id)}
                  >
                    <div className="glass-effect p-4 sm:p-6 rounded-3xl hover:scale-102 transition-all duration-500 h-full">
                      <div className={`w-12 h-12 sm:w-16 sm:h-16 bg-gradient-to-br ${template.color} rounded-2xl flex items-center justify-center mx-auto mb-3 sm:mb-4`}>
                        <template.icon className="w-6 h-6 sm:w-8 sm:h-8 text-white" />
                      </div>
                      <h3 className="text-lg sm:text-xl font-bold text-gray-800 mb-2 sm:mb-4">{template.name}</h3>
                      <p className="text-gray-600 mb-4 sm:mb-6 text-sm">{template.description}</p>
                      <div className="text-primary-500 font-semibold group-hover:text-primary-600 transition-colors">
                        Select Template →
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {selectedTemplate && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="max-w-4xl mx-auto w-full"
            >
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold text-gray-800 mb-4">
                  Generate {templates.find(t => t.id === selectedTemplate)?.name}
                </h2>
                <p className="text-gray-600">Complete 2025 Tesla Valuation Analysis Report</p>
              </div>

              <div className="glass-effect-strong p-8 rounded-3xl mb-8">
                {/* Input Form */}
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
                      placeholder="Enter current stock price"
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
                      placeholder="Enter earnings per share"
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
                      placeholder="Enter industry average PE"
                    />
                  </div>
                </div>

                <div className="flex justify-center">
                  <button
                    onClick={handleGenerateReport}
                    disabled={isGenerating}
                    className="px-8 py-4 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 text-white font-semibold rounded-xl transition-colors duration-300 flex items-center gap-2"
                  >
                    {isGenerating ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Generating...
                      </>
                    ) : (
                      <>
                        <FileText className="w-5 h-5" />
                        Generate Report
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Report Display */}
              <AnimatePresence>
                {showReport && (
                  <motion.div
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -50 }}
                    className="glass-effect-strong p-8 rounded-3xl mb-8"
                  >
                    <div className="flex items-center gap-3 mb-6">
                      <CheckCircle className="w-6 h-6 text-green-500" />
                      <h3 className="text-xl font-semibold text-gray-800">Valuation Analysis Report</h3>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                      <div className="bg-white/60 p-6 rounded-2xl text-center">
                        <div className="text-2xl font-bold text-primary-600 mb-2">{currentPE}</div>
                        <div className="text-sm text-gray-600">Current PE</div>
                      </div>
                      
                      <div className="bg-white/60 p-6 rounded-2xl text-center">
                        <div className="text-2xl font-bold text-gray-800 mb-2">{formData.industryPE}</div>
                        <div className="text-sm text-gray-600">Industry Average PE</div>
                      </div>
                      
                      <div className="bg-white/60 p-6 rounded-2xl text-center">
                        <div className={`text-2xl font-bold mb-2 ${isAboveIndustry ? 'text-orange-500' : 'text-green-500'}`}>
                          {recommendation}
                        </div>
                        <div className="text-sm text-gray-600">Investment Recommendation</div>
                      </div>
                    </div>

                    <div className="bg-white/60 p-6 rounded-2xl mb-6">
                      <h4 className="font-semibold text-gray-800 mb-3">Analysis Conclusion</h4>
                      <p className="text-gray-700 leading-relaxed">
                        {formData.company} current PE ratio is {currentPE}, {isAboveIndustry ? 'above' : 'below'} industry average of {formData.industryPE}.
                        {isAboveIndustry ? 'High valuation may reflect market expectations for future growth, but careful assessment of its reasonableness is needed.' : 'Relatively low valuation may provide good investment opportunities.'}
                      </p>
                    </div>

                    <div className="flex justify-center gap-4">
                      <button
                        onClick={handleDownload}
                        className="px-6 py-3 bg-green-500 hover:bg-green-600 text-white font-semibold rounded-xl transition-colors flex items-center gap-2"
                      >
                        <Download className="w-4 h-4" />
                        Download Report
                      </button>
                      
                      <button
                        onClick={() => navigate('/qa')}
                        className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors"
                      >
                        Ask AI
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Navigation */}
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => {
                    setSelectedTemplate(null)
                    setShowReport(false)
                  }}
                  className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Reselect Template
                </button>
                
                {showReport && (
                  <button
                    onClick={() => navigate('/qa')}
                    className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors"
                  >
                    Enter AI Q&A
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

export default ResearchLab