import React, { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

const easeInOutCubic = [0.645, 0.045, 0.355, 1.0]

const UsagePage: React.FC = () => {
  const [lines, setLines] = useState<string[]>([])

  useEffect(() => {
    const script = [
      '如何使用 Holistica Quant：',
      '1) 在场景页选择研究模板或学习主题',
      '2) 加载数据源（行情/基本面/新闻）并自动计算',
      '3) 生成报告与逻辑链，标注来源与置信度',
    ]
    let i = 0
    const id = setInterval(() => {
      if (i < script.length) {
        setLines(prev => [...prev, script[i]])
        i++
      } else {
        clearInterval(id)
      }
    }, 900)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 via-white to-cyan-50">
      <section className="relative min-h-screen snap-start overflow-hidden px-6 py-24 flex items-center">
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(900px 500px at 60% 40%, rgba(42,199,165,0.12) 0%, transparent 65%)' }} />
        <div className="max-w-6xl mx-auto w-full">
          <motion.h1 initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: easeInOutCubic }} className="text-5xl md:text-6xl font-display font-bold text-slate-900">
            使用指南
          </motion.h1>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3, duration: 0.8, ease: easeInOutCubic }} className="mt-4 text-2xl md:text-3xl text-slate-700">
            高端金融科技产品，追求流畅与质感动效。
          </motion.p>

          <div className="mt-10 glass-effect-strong rounded-3xl p-6 md:p-8 border border-primary-100">
            {lines.map((ln, idx) => (
              <motion.div key={idx} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.1, duration: 0.5 }} className="text-lg md:text-xl text-slate-800 mb-3">
                {ln}
              </motion.div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

export default UsagePage