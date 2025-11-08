import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Calculator, TrendingUp, CheckCircle, BookOpen, Target, Lightbulb } from 'lucide-react'

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

const LearningStudio: React.FC = () => {
  const navigate = useNavigate()
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [taskInput, setTaskInput] = useState('')
  const [taskResult, setTaskResult] = useState<string | null>(null)
  const [isCalculating, setIsCalculating] = useState(false)

  const tasks: Task[] = [
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

  const handleStartTask = (task: Task) => {
    setSelectedTask(task)
    setTaskInput('')
    setTaskResult(null)
  }

  const handleCalculate = () => {
    if (!taskInput.trim()) return
    
    setIsCalculating(true)
    
    setTimeout(() => {
      let result = ''
      
      if (selectedTask?.id === 'cbdc-analysis') {
        const revenueBefore = 1000 // 10 billion
        const revenueAfter = 1200 // 12 billion
        const growthRate = ((revenueAfter - revenueBefore) / revenueBefore * 100).toFixed(1)
        
        result = `Analysis Results:\n\nRevenue Growth Rate: +${growthRate}%\nBefore Revenue: $${revenueBefore}B\nAfter Revenue: $${revenueAfter}B\n\nConclusion: CBDC implementation significantly improves payment efficiency, driving digital revenue growth for banks.`
      } else if (selectedTask?.id === 'tesla-valuation') {
        const pe = 20
        const growth = 25
        const peg = (pe / growth).toFixed(2)
        const fairValue = parseFloat(peg) < 1 ? 'Undervalued' : parseFloat(peg) > 1.5 ? 'Overvalued' : 'Fair Value'
        
        result = `Valuation Analysis:\n\nCurrent PE: ${pe}\nGrowth Rate: ${growth}%\nPEG Ratio: ${peg}\n\nValuation Status: ${fairValue}\nInvestment Recommendation: ${parseFloat(peg) < 1 ? 'Buy' : parseFloat(peg) > 1.5 ? 'Hold' : 'Hold'}`
      } else if (selectedTask?.id === 'portfolio-optimization') {
        const expectedReturn = 12.5
        const risk = 8.2
        const sharpeRatio = (expectedReturn / risk).toFixed(2)
        
        result = `Portfolio Optimization Results:\n\nExpected Return: ${expectedReturn}%\nPortfolio Risk: ${risk}%\nSharpe Ratio: ${sharpeRatio}\n\nOptimization Effect: Risk-adjusted return improved by 15% compared to equal-weight allocation.`
      }
      
      setTaskResult(result)
      setIsCalculating(false)
    }, 2000)
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
          {!selectedTask && (
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
                Scenario-Based Learning Studio
              </motion.h1>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="text-lg sm:text-xl text-gray-600 mb-8 sm:mb-12"
              >
                Transform abstract knowledge into actionable tasks through real-world scenarios
              </motion.p>

              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="text-lg text-primary-600 mb-16 font-medium"
              >
                "Learn by Doing, Not by Memorizing."
              </motion.p>

              {/* Task Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6 mb-8 sm:mb-12">
                {tasks.map((task, index) => (
                  <motion.div
                    key={task.id}
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.8 + index * 0.2 }}
                    className="group cursor-pointer"
                    onClick={() => handleStartTask(task)}
                  >
                    <div className="glass-effect p-4 sm:p-6 rounded-3xl hover:scale-102 transition-all duration-500 h-full">
                      <div className="flex items-center justify-between mb-3 sm:mb-4">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                          task.difficulty === 'beginner' ? 'bg-green-100 text-green-700' :
                          task.difficulty === 'intermediate' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-red-100 text-red-700'
                        }`}>
                          {task.difficulty.charAt(0).toUpperCase() + task.difficulty.slice(1)}
                        </span>
                        <span className="text-sm text-gray-500">{task.estimatedTime}</span>
                      </div>
                      
                      <h3 className="text-lg sm:text-xl font-bold text-gray-800 mb-2 sm:mb-4">{task.title}</h3>
                      <p className="text-gray-600 mb-4 sm:mb-6 text-sm">{task.description}</p>
                      
                      <div className="space-y-2 mb-4 sm:mb-6">
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                          <Target className="w-3 h-3" />
                          <span>{task.scenario}</span>
                        </div>
                      </div>
                      
                      <div className="text-primary-500 font-semibold group-hover:text-primary-600 transition-colors">
                        Start Task →
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {selectedTask && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="max-w-4xl mx-auto w-full"
            >
              <div className="text-center mb-12">
                <h2 className="text-3xl font-bold text-gray-800 mb-4">{selectedTask.title}</h2>
                <p className="text-gray-600">{selectedTask.scenario}</p>
              </div>

              <div className="glass-effect-strong p-8 rounded-3xl mb-8">
                {/* Task Overview */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <BookOpen className="w-5 h-5" />
                    Task Overview
                  </h3>
                  <p className="text-gray-700 mb-6">{selectedTask.description}</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                    {selectedTask.dataPoints.map((point, index) => (
                      <div key={index} className="bg-white/60 p-4 rounded-xl">
                        <p className="text-sm text-gray-600">{point}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Learning Objectives */}
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

                {/* Task Input */}
                <div className="mb-8">
                  <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                    <Calculator className="w-5 h-5" />
                    Complete the Task
                  </h3>
                  
                  <div className="bg-white/60 p-6 rounded-2xl mb-4">
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

                {/* Task Result */}
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
              </div>

              {/* Navigation */}
              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setSelectedTask(null)}
                  className="px-6 py-3 border border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Back to Tasks
                </button>
                
                {taskResult && (
                  <button
                    onClick={() => navigate('/research')}
                    className="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-semibold rounded-xl transition-colors flex items-center gap-2"
                  >
                    <TrendingUp className="w-4 h-4" />
                    Start Research
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

export default LearningStudio