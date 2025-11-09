import React, { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, TrendingUp, BarChart3, Lightbulb, Bot, User, ExternalLink, RefreshCw } from 'lucide-react'
import { runQuery } from '../lib/apiClient'
import type { QueryResponse } from '../types'

interface Message {
  id: string
  type: 'user' | 'assistant'
  content: string
  data?: {
    source: string
    value: string
    timestamp: string
  }[]
  timestamp: Date
}

const QAEngine: React.FC = () => {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: 'I\'m your AI investment research assistant. Every answer I provide comes with data sources and logical analysis. What would you like to know about your investment research?',
      timestamp: new Date()
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const sampleQuestions = [
    {
      question: "Is Tesla's current PE=20 high?",
      icon: TrendingUp,
      color: "from-blue-500 to-blue-600"
    },
    {
      question: "What is the average PE ratio in the new energy vehicle industry?",
      icon: BarChart3,
      color: "from-green-500 to-green-600"
    },
    {
      question: "How to calculate the reasonable valuation range for growth stocks?",
      icon: Lightbulb,
      color: "from-orange-500 to-orange-600"
    }
  ]

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const getMockAssistantResponse = (question: string): { content: string, data?: any[] } => {
    // Simulate different responses based on question content
    if (question.includes("PE=20") || question.includes("PE=20 high")) {
      return {
        content: `Tesla's current PE ratio is 20 (data source: Sina Finance 2025-04-01), which is higher than the industry average of 15 (Bloomberg 2025Q1).

This relatively high PE ratio mainly stems from the market's optimistic expectations for Tesla's future growth. According to data from the China Association of Automobile Manufacturers, Tesla's sales are expected to grow by 25% in 2025.

It is recommended to combine PEG analysis: PEG = 20/25 = 0.8, which is less than 1, indicating that despite the high PE, considering the growth rate, Tesla's valuation is still within a reasonable range.`,
        data: [
          {
            source: "Sina Finance",
            value: "PE=20",
            timestamp: "2025-04-01"
          },
          {
            source: "Bloomberg",
            value: "Industry Average PE=15",
            timestamp: "2025Q1"
          },
          {
            source: "China Association of Automobile Manufacturers",
            value: "Expected Growth 25%",
            timestamp: "2025 Forecast"
          }
        ]
      }
    } else if (question.includes("average PE") || question.includes("industry")) {
      return {
        content: `The average PE ratio of the new energy vehicle industry is 15 (Bloomberg 2025Q1 data), but there are significant differences among companies.

Industry leader Tesla has a PE of 20, mainly due to its technological advantages and market share. In contrast, traditional automakers transitioning to new energy have relatively lower PE ratios, typically between 8-12.

It should be noted that the PE ratio of the new energy vehicle industry is generally higher than that of traditional automakers, reflecting the market's preference for the industry's growth potential.`,
        data: [
          {
            source: "Bloomberg",
            value: "Industry Average PE=15",
            timestamp: "2025Q1"
          },
          {
            source: "Wind",
            value: "Tesla PE=20",
            timestamp: "2025-04-01"
          },
          {
            source: "Industry Report",
            value: "Traditional Auto PE 8-12",
            timestamp: "2025Q1"
          }
        ]
      }
    } else {
      return {
        content: `For the valuation of growth stocks, it is recommended to use a comprehensive analysis method combining PEG (Price/Earnings to Growth ratio) and DCF (Discounted Cash Flow) models.

The PEG calculation formula is: PEG = PE ratio / Earnings growth rate. Generally speaking:
- PEG < 1: May be undervalued
- PEG = 1: Reasonable valuation
- PEG > 1: May be overvalued

At the same time, the DCF model needs to consider factors such as the company's future cash flows, discount rates, and terminal value. For high-growth companies, it is usually necessary to set different growth stages.

It is recommended to combine multiple valuation methods and consider industry characteristics, competitive landscape, and other factors for comprehensive judgment.`,
        data: [
          {
            source: "Investment Analysis",
            value: "PEG Model",
            timestamp: "Theoretical Basis"
          },
          {
            source: "Financial Analysis",
            value: "DCF Model",
            timestamp: "Valuation Method"
          },
          {
            source: "Market Practice",
            value: "Comprehensive Analysis",
            timestamp: "Best Practice"
          }
        ]
      }
    }
  }

  const fetchAssistantAnswer = async (question: string): Promise<{ content: string; data?: any[] }> => {
    try {
      const response: QueryResponse = await runQuery({
        query: question,
        scenarioOverride: 'assistant',
      })
      const assistantData = response.metadata?.assistant_answer as Record<string, any> | undefined
      const answer = assistantData?.answer ?? (response.report || '').trim()
      const supportingPoints = Array.isArray(assistantData?.supporting_points) ? assistantData.supporting_points : []
      const dataSources = Array.isArray(assistantData?.data_sources) ? assistantData.data_sources : []
      const recommended = Array.isArray(assistantData?.recommended_next_actions) ? assistantData?.recommended_next_actions : []
      const scenarioContext = assistantData?.scenario_context

      let enhancedAnswer = answer || '尚未获取到有效回答。'
      if (scenarioContext) {
        enhancedAnswer = `场景：${scenarioContext}\n\n${enhancedAnswer}`
      }
      if (recommended.length > 0) {
        enhancedAnswer += `\n\n推荐下一步：\n${recommended.map((item: string) => `- ${item}`).join('\n')}`
      }

      const evidence = dataSources.length > 0 ? dataSources : supportingPoints
      const structuredData = evidence.map((entry: string, idx: number) => ({
        source: dataSources.length > 0 ? entry : `Point ${idx + 1}`,
        value: supportingPoints[idx] ?? entry,
        timestamp: '',
      }))

      return { content: enhancedAnswer, data: structuredData }
    } catch (error) {
      console.error('QAEngine API error:', error)
      return getMockAssistantResponse(question)
    }
  }

  const handleSendMessage = async (overrideMessage?: string) => {
    const question = overrideMessage ?? inputMessage
    if (!question.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: question,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setIsTyping(true)

    const aiResponse = await fetchAssistantAnswer(question)
    const aiMessage: Message = {
      id: (Date.now() + 1).toString(),
      type: 'assistant',
      content: aiResponse.content,
      data: aiResponse.data,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, aiMessage])
    setIsTyping(false)
  }
 
   const handleSampleQuestion = (question: string) => {
    handleSendMessage(question)
  }
 
  const handleRegenerate = (messageId: string) => {
    const messageIndex = messages.findIndex(m => m.id === messageId)
    if (messageIndex === -1) return

    const userMessage = messages[messageIndex - 1]
    if (!userMessage || userMessage.type !== 'user') return

    setIsTyping(true)

    fetchAssistantAnswer(userMessage.content).then((aiResponse) => {
      const newMessage: Message = {
        id: (Date.now() + 2).toString(),
        type: 'assistant',
        content: aiResponse.content,
        data: aiResponse.data,
        timestamp: new Date()
      }

      setMessages(prev => prev.map((msg, index) => 
        index === messageIndex ? newMessage : msg
      ))
    }).finally(() => setIsTyping(false))
  }

  return (
    <div className="min-h-screen w-full relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-green-50 noise-bg">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_30%,rgba(42,199,165,0.05),transparent_50%)]" />
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

      <div className="relative z-10 flex flex-col h-screen pt-16 pb-20">
        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center mb-6 sm:mb-8"
            >
              <motion.h1
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="text-3xl sm:text-4xl lg:text-5xl font-display font-bold text-gray-800 mb-3 sm:mb-4"
              >
                Data-Aware Q&A Engine
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-lg sm:text-xl text-gray-600 mb-6 sm:mb-8"
              >
                Every answer comes with logic, data, and sources
              </motion.p>
            </motion.div>

            {/* Messages */}
            <div className="space-y-4 sm:space-y-6 mb-6 sm:mb-8">
              {messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`flex gap-3 sm:gap-4 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {message.type === 'assistant' && (
                    <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                    </div>
                  )}
                  
                  <div className={`max-w-xs sm:max-w-md lg:max-w-lg ${message.type === 'user' ? 'order-1' : ''}`}>
                    <div className={`glass-effect p-4 sm:p-6 rounded-2xl ${message.type === 'user' ? 'bg-primary-500 text-white' : 'bg-white/80 text-gray-800'}`}>
                      <p className="text-sm sm:text-base leading-relaxed whitespace-pre-line">{message.content}</p>
                      
                      {/* Data Sources */}
                      {message.data && (
                        <div className="mt-4 pt-4 border-t border-gray-200">
                          <div className="flex flex-wrap gap-2">
                            {message.data.map((item, idx) => (
                              <div
                                key={idx}
                                className="flex items-center gap-2 bg-white/60 px-3 py-2 rounded-lg text-xs text-gray-600"
                              >
                                <ExternalLink className="w-3 h-3" />
                                <span>{item.source}</span>
                                <span className="text-gray-400">•</span>
                                <span>{item.timestamp}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    {message.type === 'assistant' && (
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          onClick={() => handleRegenerate(message.id)}
                          className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                        >
                          <RefreshCw className="w-3 h-3" />
                          Regenerate
                        </button>
                      </div>
                    )}
                  </div>
                  
                  {message.type === 'user' && (
                    <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
                      <User className="w-4 h-4 sm:w-5 sm:h-5 text-gray-600" />
                    </div>
                  )}
                </motion.div>
              ))}

              {/* Typing Indicator */}
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-4 justify-start"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center">
                    <Bot className="w-5 h-5 text-white" />
                  </div>
                  
                  <div className="glass-effect bg-white/80 p-6 rounded-2xl">
                    <div className="flex space-x-2">
                      <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" />
                      <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                      <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                    </div>
                  </div>
                </motion.div>
              )}
            </div>

            {/* Sample Questions */}
            {messages.length === 1 && (
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="mb-6 sm:mb-8"
              >
                <h3 className="text-lg sm:text-xl font-semibold text-gray-800 mb-4 sm:mb-6 text-center">
                  Try asking these questions
                </h3>
                
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
                  {sampleQuestions.map((item, index) => (
                    <motion.button
                      key={index}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.8 + index * 0.2 }}
                      onClick={() => handleSampleQuestion(item.question)}
                      className="glass-effect p-4 rounded-2xl text-left hover:scale-105 transition-all duration-300 group"
                    >
                      <div className={`w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br ${item.color} rounded-xl flex items-center justify-center mb-3 sm:mb-4`}>
                        <item.icon className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                      </div>
                      <p className="text-gray-800 font-medium text-sm sm:text-base mb-2">{item.question}</p>
                      <div className="text-primary-500 text-xs sm:text-sm group-hover:text-primary-600 transition-colors">
                        Click to ask →
                      </div>
                    </motion.button>
                  ))}
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Area */}
        <div className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-lg border-t border-gray-200/50 px-4 sm:px-6 lg:px-8 py-4">
          <div className="max-w-4xl mx-auto">
            <div className="flex gap-3 sm:gap-4 items-end">
              <div className="flex-1">
                <textarea
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  placeholder="Ask any investment research question..."
                  className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none max-h-32"
                  rows={1}
                />
              </div>
              
              <button
                onClick={handleSendMessage}
                disabled={!inputMessage.trim()}
                className="px-4 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 text-white rounded-2xl transition-colors flex items-center justify-center"
              >
                <Send className="w-4 h-4 sm:w-5 sm:h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default QAEngine