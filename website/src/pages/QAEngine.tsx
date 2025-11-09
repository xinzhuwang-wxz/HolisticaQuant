import React, { useState, useRef, useEffect } from 'react'
import { AnimatePresence, LayoutGroup, motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Send, TrendingUp, BarChart3, Lightbulb, Bot, User, ExternalLink, RefreshCw } from 'lucide-react'
import { getWebSocketBase, runQuery } from '../lib/apiClient'
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
  segments?: { title: string; content?: string }[]
  isStreaming?: boolean
}

interface AssistantReply {
  content: string
  data?: { source: string; value: string; timestamp: string }[]
  structured?: {
    scenario?: string
    supportingPoints: string[]
    nextActions: string[]
    dataSources: string[]
  }
}

const QAEngine: React.FC = () => {
  const navigate = useNavigate()
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'assistant',
      content: '我是你的投研助手，会同时给出结论、数据来源和推理过程。想了解哪家公司的投资问题？',
      timestamp: new Date()
    }
  ])
  const [inputMessage, setInputMessage] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null)

  const sampleQuestions = [
    {
      question: "宁德时代的当前估值是否偏高？",
      icon: TrendingUp,
      color: "from-blue-500 to-blue-600"
    },
    {
      question: "半导体龙头中芯国际的估值关键驱动是什么？",
      icon: BarChart3,
      color: "from-green-500 to-green-600"
    },
    {
      question: "如何快速判断国产AI龙头的合理估值区间？",
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

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [])

  const buildAssistantReply = (response: QueryResponse): AssistantReply => {
    const assistantMeta = (response.metadata?.assistant_answer ?? null) as
      | {
          scenario_context?: string
          answer: string
          supporting_points?: string[]
          recommended_next_actions?: string[]
          data_sources?: string[]
        }
      | null

    if (assistantMeta) {
      const sections: string[] = []
      if (assistantMeta.scenario_context) {
        sections.push(`【场景】\n${assistantMeta.scenario_context}`)
      }
      if (assistantMeta.answer) {
        sections.push(`【回答】\n${assistantMeta.answer}`)
      }
      if (assistantMeta.supporting_points?.length) {
        sections.push(
          `【支撑要点】\n${assistantMeta.supporting_points
            .map((item) => `• ${item}`)
            .join('\n')}`
        )
      }
      if (assistantMeta.recommended_next_actions?.length) {
        sections.push(
          `【下一步行动】\n${assistantMeta.recommended_next_actions
            .map((item) => `• ${item}`)
            .join('\n')}`
        )
      }
      if (assistantMeta.data_sources?.length) {
        sections.push(
          `【数据来源】\n${assistantMeta.data_sources.map((item) => `• ${item}`).join('\n')}`
        )
      }

      const dataSourcesPayload = assistantMeta.data_sources?.map((source) => ({
        source,
        value: '',
        timestamp: '',
      }))

      return {
        content: sections.join('\n\n').trim(),
        data: dataSourcesPayload,
        structured: {
          scenario: assistantMeta.scenario_context,
          supportingPoints: assistantMeta.supporting_points ?? [],
          nextActions: assistantMeta.recommended_next_actions ?? [],
          dataSources: assistantMeta.data_sources ?? [],
        },
      }
    }

    return {
      content: response.report || '（暂无回答）',
      structured: {
        scenario: undefined,
        supportingPoints: [],
        nextActions: [],
        dataSources: [],
      },
    }
  }

  const fetchAssistantAnswerHttp = async (
    question: string,
  ): Promise<{ reply: AssistantReply; scenario: QueryResponse['scenario_type'] }> => {
    try {
      const response: QueryResponse = await runQuery({ query: question })
      return { reply: buildAssistantReply(response), scenario: response.scenario_type }
    } catch (error) {
      console.error('QAEngine HTTP fallback error:', error)
      return { reply: { content: '暂时无法获取回答，请稍后重试。' }, scenario: 'assistant' }
    }
  }

  const handleSendMessage = async (overrideMessage?: string) => {
    const rawQuestion = overrideMessage ?? inputMessage
    const question = rawQuestion.trim()
    if (!question || streamingMessageId) return

    const newId = Date.now().toString()
    setInputMessage('')

    const userMessage: Message = {
      id: newId,
      type: 'user',
      content: question,
      timestamp: new Date()
    }

    const assistantPlaceholder: Message = {
      id: `assistant-${Date.now()}`,
      type: 'assistant',
      content: '',
      segments: [],
      isStreaming: true,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage, assistantPlaceholder])
    setIsTyping(true)

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const appendStreamSegment = (title: string, body?: string) => {
      const truncate = (text: string, max = 260) =>
        text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`

      const finalText = body ? truncate(body) : ''

      let targetIndex = -1
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== assistantPlaceholder.id) return msg
          const segments = [...(msg.segments ?? []), { title, content: finalText ? '' : undefined }]
          targetIndex = segments.length - 1
          return {
            ...msg,
            segments,
          }
        })
      )

      if (!finalText) {
        return
      }

      const chars = finalText.split('')
      let charPointer = 0
      const interval = 18

      const typewriter = () => {
        charPointer += 1
        const partial = finalText.slice(0, charPointer)
        setMessages((prev) =>
          prev.map((msg) => {
            if (msg.id !== assistantPlaceholder.id || targetIndex < 0 || !msg.segments) return msg
            const segments = msg.segments.map((segment, idx) =>
              idx === targetIndex ? { ...segment, content: partial } : segment
            )
            return { ...msg, segments }
          })
        )

        if (charPointer < chars.length) {
          window.setTimeout(typewriter, interval)
        }
      }

      window.setTimeout(typewriter, interval)
    }

    const handleFinal = (reply: AssistantReply) => {
      const segments: { title: string; content?: string }[] = []

      if (reply.structured?.scenario) {
        segments.push({ title: '场景', content: reply.structured.scenario })
      }
      if (reply.content) {
        segments.push({ title: '回答', content: reply.content })
      }
      if (reply.structured?.supportingPoints?.length) {
        segments.push({ title: '支撑要点', content: reply.structured.supportingPoints.join('\n') })
      }
      if (reply.structured?.nextActions?.length) {
        segments.push({ title: '下一步行动', content: reply.structured.nextActions.join('\n') })
      }
      if (reply.structured?.dataSources?.length) {
        segments.push({ title: '数据来源', content: reply.structured.dataSources.join('\n') })
      }

      if (segments.length === 0) {
        segments.push({ title: '回答', content: reply.content || '（暂无）' })
      }

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantPlaceholder.id
            ? {
                ...msg,
                content: '',
                data: reply.data,
                segments: msg.segments,
                isStreaming: true,
              }
            : msg
        )
      )

      const perCharInterval = 18
      let delay = 0
      segments.forEach((segment) => {
        setTimeout(() => {
          appendStreamSegment(segment.title, segment.content)
        }, delay)
        delay += Math.max(480, (segment.content?.length ?? 0) * perCharInterval)
      })

      setTimeout(() => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantPlaceholder.id
              ? {
                  ...msg,
                  isStreaming: false,
                  timestamp: new Date(),
                }
              : msg
          )
        )
      }, delay)
    }

    const wsUrl = `${getWebSocketBase()}/api/query/stream`
    try {
      const socket = new WebSocket(wsUrl)
      wsRef.current = socket
      let finalReceived = false

      socket.onopen = () => {
        const payload = {
          query: question,
          context: {
            conversation_mode: 'qa_engine',
          },
        }
        socket.send(JSON.stringify(payload))
      }

      socket.onmessage = async (event) => {
        try {
          const data = JSON.parse(event.data) as { type: string; [key: string]: any }
          if (data.type === 'status') {
            if (data.message) {
              appendStreamSegment('状态', data.message)
            }
          } else if (data.type === 'timeline') {
            appendStreamSegment(data.title ?? '进度', data.content)
          } else if (data.type === 'final') {
            finalReceived = true
            const response = data.payload as QueryResponse
            handleFinal(buildAssistantReply(response))
            setIsTyping(false)
            setStreamingMessageId(null)
            socket.close()
          } else if (data.type === 'error') {
            appendStreamSegment('错误', data.message)
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantPlaceholder.id
                  ? {
                      ...msg,
                      content: data.message,
                      isStreaming: false,
                      timestamp: new Date(),
                    }
                  : msg
              )
            )
            setIsTyping(false)
            setStreamingMessageId(null)
            socket.close()
          }
        } catch (err) {
          console.error('QAEngine stream parse error:', err)
        }
      }

      socket.onerror = async () => {
        socket.close()
        if (!finalReceived) {
          const fallback = await fetchAssistantAnswerHttp(question)
          handleFinal(fallback.reply)
          setIsTyping(false)
          setStreamingMessageId(null)
          wsRef.current = null
        }
      }

      socket.onclose = async () => {
        if (!finalReceived) {
          const fallback = await fetchAssistantAnswerHttp(question)
          handleFinal(fallback.reply)
          setIsTyping(false)
        }
        setStreamingMessageId(null)
        wsRef.current = null
      }
    } catch (error) {
      console.error('QAEngine websocket init error:', error)
      const fallback = await fetchAssistantAnswerHttp(question)
      handleFinal(fallback.reply)
      setIsTyping(false)
      setStreamingMessageId(null)
      wsRef.current = null
    }
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

    fetchAssistantAnswerHttp(userMessage.content)
      .then(({ reply }) => {
        const segments: { title: string; content?: string }[] = []

        if (reply.structured?.scenario) {
          segments.push({ title: '场景', content: reply.structured.scenario })
        }
        if (reply.content) {
          segments.push({ title: '回答', content: reply.content })
        }
        if (reply.structured?.supportingPoints?.length) {
          segments.push({ title: '支撑要点', content: reply.structured.supportingPoints.join('\n') })
        }
        if (reply.structured?.nextActions?.length) {
          segments.push({ title: '下一步行动', content: reply.structured.nextActions.join('\n') })
        }
        if (reply.structured?.dataSources?.length) {
          segments.push({ title: '数据来源', content: reply.structured.dataSources.join('\n') })
        }

        const newMessage: Message = {
          id: (Date.now() + 2).toString(),
          type: 'assistant',
          content: '',
          data: reply.data,
          segments,
          timestamp: new Date(),
        }

        setMessages((prev) => prev.map((msg, index) => (index === messageIndex ? newMessage : msg)))
      })
      .finally(() => setIsTyping(false))
  }

  return (
    <div className="min-h-screen w-full relative overflow-x-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-white to-green-50 noise-bg">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_70%_30%,rgba(42,199,165,0.05),transparent_50%)]" />
      </div>

      <div className="relative z-10 p-4 sm:p-6">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 text-gray-600 hover:text-primary-600 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          返回首页
        </button>
      </div>

      <LayoutGroup>
        <div className="relative z-10 flex flex-col min-h-screen pt-16 pb-28">
          <div className="flex-1 px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 gap-6 justify-items-center" style={{ minHeight: 0 }}>
              <div className="flex flex-col h-full min-h-0">
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
                    数据觉察型投研问答机
                  </motion.h1>

                  <motion.p
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.4 }}
                    className="text-lg sm:text-xl text-gray-600 mb-6 sm:mb-8"
                  >
                    每一次回答都同步展示结论、逻辑链与数据来源
                  </motion.p>
                </motion.div>

                <div className="flex-1 overflow-y-auto pr-0 lg:pr-4 min-h-0">
                  <div className="max-w-4xl mx-auto">
                    <div className="space-y-4 sm:space-y-6 pb-6">
                      {messages.map((message, index) => (
                        <motion.div
                          key={message.id}
                          layout
                          layoutId={message.id === streamingMessageId ? 'active-query' : undefined}
                          initial={{ opacity: 0, y: 30 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: index * 0.08 }}
                          className={`flex gap-3 sm:gap-4 ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          {message.type === 'assistant' && (
                            <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center flex-shrink-0">
                              <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
                            </div>
                          )}

                          <div className={`max-w-xs sm:max-w-md lg:max-w-lg ${message.type === 'user' ? 'order-1' : ''}`}>
                            <div
                              className={`glass-effect p-4 sm:p-6 rounded-2xl shadow-[0_12px_30px_rgba(20,20,40,0.18)] ${
                                message.type === 'user'
                                  ? 'bg-white text-gray-800 border border-primary-200'
                                  : 'bg-white/85 text-gray-800'
                              }`}
                            >
                              {message.content && (
                                <p className="text-sm sm:text-base leading-relaxed whitespace-pre-line">
                                  {message.content}
                                </p>
                              )}

                              {message.segments && message.segments.length > 0 && (
                                <div className={`space-y-3 ${message.content ? 'mt-4 pt-4 border-t border-gray-200/70' : ''}`}>
                                  {message.segments.map((segment, segIdx) => (
                                    <div key={`${message.id}-segment-${segIdx}`}>
                                      <div className="text-xs font-semibold uppercase tracking-[0.3em] text-primary-500/70 mb-1">
                                        {segment.title}
                                      </div>
                                      {segment.content && (
                                        <div className="text-sm leading-relaxed whitespace-pre-line text-gray-700">
                                          {segment.content}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}

                              {message.data && message.data.length > 0 && (
                                <div className="mt-4 pt-4 border-t border-gray-200/70">
                                  <div className="flex flex-wrap gap-2">
                                    {message.data.map((item, idx) => (
                                      <div
                                        key={idx}
                                        className="flex items-center gap-2 bg-white/70 px-3 py-2 rounded-lg text-xs text-gray-600"
                                      >
                                        <ExternalLink className="w-3 h-3" />
                                        <span>{item.source}</span>
                                        {item.timestamp && (
                                          <>
                                            <span className="text-gray-400">•</span>
                                            <span>{item.timestamp}</span>
                                          </>
                                        )}
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
                                  重新生成
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

                      <div ref={messagesEndRef} />
                    </div>
                  </div>
                </div>

                {messages.length === 1 && (
                  <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                    className="mt-4 mb-8"
                  >
                    <h3 className="text-lg sm:text-xl font-semibold text-gray-800 mb-4 sm:mb-6 text-center">
                      不妨先试试这些典型问题
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
                            一键提问 →
                          </div>
                        </motion.button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          </div>

          <div className="fixed bottom-0 left-0 right-0 bg-white/80 backdrop-blur-lg border-t border-gray-200/50 px-4 sm:px-6 lg:px-8 py-4">
            <div className="max-w-4xl mx-auto relative">
              <AnimatePresence>
                {streamingMessageId && (
                  <motion.div
                    layoutId="active-query"
                    initial={{ opacity: 0, y: 24, scale: 0.95 }}
                    animate={{ opacity: 1, y: -12, scale: 1 }}
                    exit={{ opacity: 0, y: 20, scale: 0.96 }}
                    transition={{ duration: 0.35, ease: 'easeOut' }}
                    className="absolute left-0 right-0 mx-auto -top-24 max-w-xl glass-effect bg-primary-500/90 text-white shadow-[0_18px_45px_rgba(20,60,90,0.25)] px-5 py-4 rounded-2xl text-sm sm:text-base leading-relaxed"
                  >
                    {/* This div is now managed by the streamingContentRef.current */}
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="flex gap-3 sm:gap-4 items-end">
                <div className="flex-1">
                  <textarea
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        handleSendMessage()
                      }
                    }}
                    placeholder="请输入想研究的公司、指标或投资问题..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-2xl focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none max-h-32"
                    rows={1}
                  />
                </div>

                <button
                  onClick={() => handleSendMessage()}
                  disabled={!inputMessage.trim()}
                  className="px-4 py-3 bg-primary-500 hover:bg-primary-600 disabled:bg-gray-300 text-white rounded-2xl transition-colors flex items-center justify-center"
                >
                  <Send className="w-4 h-4 sm:w-5 sm:h-5" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </LayoutGroup>
    </div>
  )
}

export default QAEngine