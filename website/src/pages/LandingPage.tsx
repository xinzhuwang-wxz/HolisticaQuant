import React, { useEffect, useState } from 'react'
import { motion, useAnimation } from 'framer-motion'
import MagneticButton from '../components/MagneticButton'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ChevronDown } from 'lucide-react'

const sectionVariants = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0 },
}

const easeInOutCubic = [0.645, 0.045, 0.355, 1.0]

const LandingPage: React.FC = () => {
  const navigate = useNavigate()
  const titleControls = useAnimation()
  const [breathing, setBreathing] = useState(false)
  const [activeDemo, setActiveDemo] = useState<'learning' | 'research' | 'companion' | null>(null)

  const titleLayout = [
    { letters: 'Holistica'.split(''), anchorIndex: 4 },
    { letters: 'Quant'.split(''), anchorIndex: 2 },
  ]

  const lettersAppearDelay = (layout: typeof titleLayout) => {
    return layout.reduce((maxDelay, { letters, anchorIndex }, lineIdx) => {
      const lineDelay = lineIdx * 0.5
      const maxOffset = letters.reduce((acc, _, idx) => Math.max(acc, Math.abs(anchorIndex - idx)), 0)
      const letterDelay = maxOffset * 0.08
      return Math.max(maxDelay, lineDelay + letterDelay)
    }, 0)
  }

  const letterVariants = {
    hidden: (custom: { offset: number }) => ({
      opacity: 0,
      x: (custom?.offset ?? 0) * 36,
      y: 20,
      scale: 0.92,
      filter: 'blur(14px)',
    }),
    visible: (custom: { offset: number }) => ({
      opacity: 1,
      x: 0,
      y: 0,
      scale: 1,
      filter: 'blur(0px)',
      transition: {
        duration: 0.5,
        ease: easeInOutCubic,
        delay: Math.abs(custom?.offset ?? 0) * 0.08,
      },
    }),
  }

  const lineVariants = {
    hidden: { opacity: 0 },
    visible: (custom: { lineIdx: number }) => ({
      opacity: 1,
      transition: {
        delayChildren: (custom?.lineIdx ?? 0) * 0.5,
        staggerChildren: 0.08,
      },
    }),
  }

  type DemoEntry = {
    role: 'user' | 'assistant' | 'note'
    content: string
  }

  const accentThemes = {
    teal: {
      gradient: 'from-[#4dd6bf] via-[#35c1aa] to-[#22a790] ',
      cardClass: 'bg-white/95 text-slate-800 border border-white/60 shadow-[0_28px_70px_rgba(30,150,135,0.18)] backdrop-blur-lg',
      userBubbleClass: 'bg-slate-900/5 border border-slate-900/10 text-slate-700',
      labelClass: 'text-teal-600/80',
      noteClass: 'text-teal-500/70',
      footerClass: 'text-slate-400/75',
      isDark: false,
    },
    blue: {
      gradient: 'from-[#6aa8ff] via-[#4a8dee] to-[#3a74d0]',
      cardClass: 'bg-white/92 text-slate-800 border border-white/55 shadow-[0_30px_80px_rgba(30,90,180,0.18)] backdrop-blur-lg',
      userBubbleClass: 'bg-slate-900/5 border border-slate-900/10 text-slate-700',
      labelClass: 'text-sky-600/80',
      noteClass: 'text-sky-500/70',
      footerClass: 'text-slate-400/75',
      isDark: false,
    },
    violet: {
      gradient: 'from-[#ba9dff] via-[#a17bff] to-[#8c63f5]',
      cardClass: 'bg-white/94 text-slate-800 border border-white/55 shadow-[0_30px_80px_rgba(110,70,200,0.2)] backdrop-blur-lg',
      userBubbleClass: 'bg-slate-900/5 border border-slate-900/10 text-slate-700',
      labelClass: 'text-violet-600/80',
      noteClass: 'text-violet-500/70',
      footerClass: 'text-slate-400/75',
      isDark: false,
    },
  } as const

  type AccentKey = keyof typeof accentThemes

  const ScenarioDemo: React.FC<{ script: DemoEntry[]; accent: AccentKey; isActive: boolean }> = ({ script, accent, isActive }) => {
    const theme = accentThemes[accent]
    const [visibleMessages, setVisibleMessages] = useState<DemoEntry[]>([])
    const [typingMessage, setTypingMessage] = useState<DemoEntry | null>(null)

    useEffect(() => {
      if (!isActive) {
        setVisibleMessages([])
        setTypingMessage(null)
        return
      }

      let messageIndex = 0
      let charIndex = 0
      let timeoutId: ReturnType<typeof setTimeout>
      let cancelled = false

      const schedule = (delay: number) => {
        timeoutId = setTimeout(typeNext, delay)
      }

      const typeNext = () => {
        if (cancelled) return
        if (messageIndex >= script.length) {
          setTypingMessage(null)
          return
        }

        const current = script[messageIndex]

        if (current.role === 'note') {
          setVisibleMessages((prev) => [...prev, current])
          messageIndex += 1
          schedule(360)
          return
        }

        if (charIndex <= current.content.length) {
          setTypingMessage({
            role: current.role,
            content: current.content.slice(0, charIndex),
          })
          charIndex += 1
          schedule(current.role === 'assistant' ? 26 : 32)
        } else {
          setVisibleMessages((prev) => [...prev, current])
          setTypingMessage(null)
          messageIndex += 1
          charIndex = 0
          schedule(480)
        }
      }

      schedule(260)

      return () => {
        cancelled = true
        clearTimeout(timeoutId)
      }
    }, [script, isActive])

    const renderMessage = (message: DemoEntry, key: React.Key, isTyping = false) => {
      if (message.role === 'note') {
        return (
          <div
            key={key}
            className={`self-center text-[0.65rem] uppercase tracking-[0.4em] pt-2 ${theme.noteClass}`}
          >
            {message.content}
          </div>
        )
      }

      const baseClass =
        message.role === 'assistant'
          ? `self-end bg-gradient-to-r ${theme.gradient} text-white`
          : `self-start ${theme.userBubbleClass}`

      return (
        <div
          key={key}
          className={`${baseClass} rounded-2xl px-4 py-3 max-w-full lg:max-w-[78%] shadow-[0_18px_45px_rgba(12,20,40,0.35)] backdrop-blur-md whitespace-pre-wrap`}
        >
          <span className="text-sm leading-relaxed">
            {message.content}
            {isTyping && <span className="animate-pulse ml-1">▌</span>}
          </span>
        </div>
      )
    }

    return (
      <div className="w-full h-full flex flex-col justify-center">
        <div className={`relative rounded-[32px] px-6 py-6 min-h-[360px] ${theme.cardClass}`}>
          <div className={`absolute -top-3 left-6 px-3 py-1 rounded-full text-[0.65rem] uppercase tracking-[0.3em] ${theme.labelClass} bg-white/15`}>Prototype Sequence</div>
          <div className="flex flex-col gap-3 pt-6">
            {visibleMessages.map((msg, idx) => renderMessage(msg, `visible-${idx}`))}
            {typingMessage && renderMessage(typingMessage, 'typing', true)}
          </div>
          <div className={`mt-6 text-xs text-right tracking-[0.25em] uppercase ${theme.footerClass}`}>
            * 演示数据
          </div>
        </div>
      </div>
    )
  }

  const LEARNING_DEMO_SCRIPT: DemoEntry[] = [
    { role: 'user', content: '🔍 我想学习「区块链支付 / CBDC 试点」这个知识点。' },
    { role: 'assistant', content: '📚 场景摘要：\n• 2025 重点城市：上海 / 深圳 / 成都\n• 数字钱包开通：1.1 亿\n• 交易笔数：2.8 亿\n以上数据来自课程内置资料包。' },
    { role: 'user', content: '🧮 微型实验：输入数字化收入 10 亿 → 12 亿。' },
    { role: 'assistant', content: '🧠 实验结论：数字化收入提升 20%。\n分析要点：\n1. 支付耗时缩短 30%\n2. 对公结算满意度 +12%\n3. 输出学习卡片与讨论问题。' },
    { role: 'note', content: '步骤提示 · 关键指标 · 复盘建议' },
  ]

  const RESEARCH_DEMO_SCRIPT: DemoEntry[] = [
    { role: 'user', content: '📝 启动模板：「公司估值报告」→ 特斯拉 2025。' },
    { role: 'assistant', content: '📊 参数填充：\n• 股价：200 USD\n• EPS：10 USD\n• 行业 PE：15\n• 自定义假设：销量增长 25%，毛利率 18%。' },
    { role: 'user', content: '🧾 请生成完整报告结构。' },
    { role: 'assistant', content: '📑 报告草稿片段：\n1. 摘要：维持 Hold，目标价 215。\n2. 财务：PE 20｜PEG 0.8｜ROE 23%。\n3. 行业：高于同业均值 15 的合理性来自交付弹性。\n4. 风险：产能扩张、原材料、汇率。\n5. 下一步：跟踪 FCF、4680 电池进度。' },
    { role: 'note', content: '模板参数 · 指标计算 · 风险清单' },
  ]

  const COMPANION_DEMO_SCRIPT: DemoEntry[] = [
    { role: 'user', content: '💬 PE = 20 算高吗？' },
    { role: 'assistant', content: '💡 结论：当前 PE 20，高于行业均值 15。支撑理由：\n• 新能源销量目标 +25%\n• 服务收入增速 +32%\n• 自由现金流转正。' },
    { role: 'user', content: '🔁 如果销量没有达标呢？' },
    { role: 'assistant', content: '🛡️ 情景分析：销量仅增 12% 时，模型给出 PE 合理区间 15~16，建议仓位下调 10%。' },
    { role: 'assistant', content: '📎 数据出处：教学行情 2025-04-01；行业均值样本（12 家车企）；销售规划周报。' },
    { role: 'note', content: '问答轨迹 · 数据引用 · 风险提醒' },
  ]

  useEffect(() => {
    const runSequence = async () => {
      await titleControls.start('visible')
      setBreathing(true)
      setActiveDemo('learning')
    }

    runSequence()
  }, [titleControls])

  return (
    <div className="h-screen w-screen overflow-y-scroll snap-y snap-mandatory bg-gradient-to-br from-slate-50 via-white to-cyan-50/30">
      {/* Hero Section – Cinematic Brand Entry */}
      <section className="relative h-screen snap-start overflow-hidden">
        {/* Atmospheric background */}
        <div className="absolute inset-0 noise-bg" />
        <div className="absolute inset-0 bg-gradient-to-br from-[#0A1A2F] via-[#0F2744] to-cyan-600/20" />
        {/* Cinematic fog intro */}
        <motion.div
          className="absolute inset-0 pointer-events-none bg-gradient-to-br from-[#040910] via-[#09172A] to-[#123456]"
          initial={{ opacity: 1 }}
          animate={{ opacity: [1, 0.9, 0.55, 0.15, 0.05] }}
          transition={{ duration: 3.6, ease: easeInOutCubic }}
        />
        <motion.div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(1200px 650px at 50% 45%, rgba(42,199,165,0.28) 0%, rgba(42,199,165,0.12) 40%, transparent 72%)' }}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.25, 0.6, 1] }}
          transition={{ delay: 0.7, duration: 2.4, ease: easeInOutCubic }}
        />
        <motion.div
          className="absolute inset-0 pointer-events-none"
          initial={{ opacity: 0, scale: 1.25 }}
          animate={{ opacity: [0, 0.3, 0], scale: [1.25, 1.08, 1] }}
          transition={{ delay: 0.3, duration: 2.8, ease: easeInOutCubic }}
          style={{
            background: 'radial-gradient(closest-side, rgba(255,255,255,0.6), rgba(255,255,255,0) 70%)',
            filter: 'blur(90px)'
          }}
        />

        {/* Floating ambient orbs */}
        {[...Array(8)].map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-24 h-24 bg-primary-500/10 rounded-full blur-3xl"
            initial={{ opacity: 0.6 }}
            animate={{ opacity: [0.6, 1, 0.6], y: [0, -12, 0], scale: [1, 1.05, 1] }}
            transition={{ delay: i * 0.3, duration: 8, repeat: Infinity, repeatType: 'mirror', ease: easeInOutCubic }}
            style={{ left: `${(i * 9) % 90}%`, top: `${(i * 13) % 80}%` }}
          />
        ))}

        <div className="relative z-10 h-full flex flex-col items-center justify-center px-6">
          {/* Cinematic Title */}
          <motion.div
            className="relative w-full max-w-6xl mx-auto flex flex-col items-center min-h-[70vh]"
            style={{ perspective: 1800 }}
          >
            <motion.div
              className="absolute -z-10"
              initial={{ opacity: 0.75, scale: 1.05 }}
              animate={{ opacity: [0.75, 0.6, 0.85], scale: [1.05, 1.12, 1.04] }}
              transition={{ duration: 8, repeat: Infinity, repeatType: 'mirror', ease: easeInOutCubic }}
              style={{
                width: '70vw',
                height: '70vw',
                borderRadius: '50%',
                filter: 'blur(70px)',
                background: 'radial-gradient(closest-side, rgba(100,255,208,0.16), rgba(42,199,165,0.12) 55%, transparent 78%)',
              }}
            />
            <motion.div
              className="absolute inset-0 pointer-events-none"
              animate={breathing ? {
                opacity: [0, 0.35, 0],
                x: [-280, 300],
                transition: { duration: 4.8, ease: easeInOutCubic, repeat: Infinity, repeatDelay: 5 }
              } : { opacity: 0 }}
              style={{
                background: 'radial-gradient(60% 140% at 50% 50%, rgba(255,255,255,0.78) 0%, rgba(180,248,230,0.38) 40%, rgba(255,255,255,0) 100%)',
                mixBlendMode: 'screen',
                filter: 'blur(35px)'
              }}
            />
            <motion.div
              animate={breathing ? {
                scale: [1, 1.012, 1],
                filter: [
                  'drop-shadow(0 24px 72px rgba(10,26,47,0.5))',
                  'drop-shadow(0 32px 92px rgba(42,199,165,0.58))',
                  'drop-shadow(0 26px 74px rgba(10,26,47,0.52))'
                ],
                transition: { duration: 3.6, ease: easeInOutCubic, repeat: Infinity }
              } : undefined}
              className="flex flex-col items-center gap-8 mt-16"
            >
              {titleLayout.map(({ letters, anchorIndex }, lineIdx) => (
                <motion.div
                  key={`line-${lineIdx}`}
                  variants={lineVariants}
                  initial="hidden"
                  animate={titleControls}
                  custom={{ lineIdx }}
                  className="flex justify-center gap-[0.3em] text-[16vw] leading-none md:text-[9vw] font-display font-bold uppercase"
                >
                  {letters.map((char, charIdx) => (
                    <motion.span
                      key={`char-${lineIdx}-${charIdx}`}
                      variants={letterVariants}
                      custom={{ offset: anchorIndex - charIdx }}
                      className="text-transparent bg-clip-text"
                      style={{
                        backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.98), rgba(163,250,226,0.9) 35%, rgba(42,199,165,0.82) 70%, rgba(25,50,84,0.95))',
                        textShadow: '0 35px 100px rgba(8,18,32,0.68), 0 18px 52px rgba(42,199,165,0.5), 0 0 22px rgba(255,255,255,0.75)'
                      }}
                    >
                      {char}
                    </motion.span>
                  ))}
                </motion.div>
              ))}
              <motion.p
                initial={{ opacity: 0, y: 32 }}
                animate={titleControls}
                variants={{
                  hidden: { opacity: 0, y: 32 },
                  visible: {
                    opacity: 1,
                    y: 0,
                    transition: { delay: lettersAppearDelay(titleLayout) + 0.25, duration: 0.9, ease: easeInOutCubic },
                  },
                }}
                className="text-[3.6vw] md:text-[2.4rem] text-center tracking-[0.32em] uppercase"
                style={{
                  backgroundImage: 'linear-gradient(120deg, rgba(180,255,238,0.9), rgba(120,248,214,0.75), rgba(255,255,255,0.9))',
                  WebkitBackgroundClip: 'text',
                  color: 'transparent',
                  textShadow: '0 24px 60px rgba(10,26,47,0.48), 0 0 18px rgba(120,248,214,0.55)'
                }}
              >
                AI-powered Insight Investment Lab
              </motion.p>
            </motion.div>
          </motion.div>

          {/* Scroll hint */}
          <div className="absolute bottom-10 left-1/2 -translate-x-1/2 text-slate-300">
            <div className="flex flex-col items-center">
              <span className="text-sm mb-2">Welcome to Future</span>
              <ChevronDown className="w-6 h-6 animate-bounce" />
            </div>
          </div>
        </div>
      </section>

        {/* Scene 1 – Learning Studio */}
      <section className="relative h-screen snap-start overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#e8f6f1] via-[#f1f4ff] to-[#dcecf8]" />
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(920px 540px at 22% 74%, rgba(46,180,160,0.22) 0%, transparent 70%)' }} />

        <motion.div
          variants={sectionVariants}
          initial="initial"
          whileInView="animate"
          viewport={{ once: false, amount: 0.45 }}
          transition={{ duration: 0.6 }}
          className="relative z-10 h-full flex items-center"
          onViewportEnter={() => setActiveDemo('learning')}
          onViewportLeave={() => setActiveDemo((prev) => (prev === 'learning' ? null : prev))}
        >
          <div className="max-w-7xl mx-auto w-full px-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="space-y-6">
                <h2 className="text-5xl md:text-[3rem] font-display font-bold text-slate-900">
                  事件驱动的学习实验室
                </h2>
                <p className="text-slate-600 leading-relaxed">
                  让知识点与真实事件组合成“可练任务”，完成选题、实验、验证的闭环体验。
                </p>
                <ul className="space-y-3 text-slate-600">
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-teal-400/80" />
                    <span>实时事件 + 微型实验 → 从“区块链支付 / CBDC” 中提炼任务与验证路径。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-teal-400/80" />
                    <span>AI 指导分步输入、计算、验证，强调“先理解，再动手”。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-teal-400/80" />
                    <span>教学素材即可驱动体验，稍后接入真实数据源时无缝衔接。</span>
                  </li>
                </ul>
                <div className="grid grid-cols-3 gap-3 pt-2">
                  {[
                    { title: 'STEP 01', desc: '选择知识点' },
                    { title: 'STEP 02', desc: '加载事件素材' },
                    { title: 'STEP 03', desc: '动手实验 + 验证' },
                  ].map((item) => (
                    <div key={item.title} className="rounded-xl bg-white shadow-[0_12px_35px_rgba(40,120,110,0.12)] border border-white/80 px-4 py-3">
                      <div className="text-xs uppercase tracking-[0.35em] text-primary-500/80">{item.title}</div>
                      <div className="text-sm font-semibold text-slate-700 mt-2">{item.desc}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <ScenarioDemo script={LEARNING_DEMO_SCRIPT} accent="teal" isActive={activeDemo === 'learning'} />
              </div>
            </div>
          </div>
        </motion.div>
      </section>

        {/* Scene 2 – Research Lab (Tension) */}
      <section className="relative h-screen snap-start overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#e6efff] via-[#eef4ff] to-[#d9edff]" />
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'linear-gradient(120deg, rgba(120,170,250,0.22), transparent 62%), radial-gradient(920px 520px at 72% 38%, rgba(140,185,255,0.25) 0%, transparent 70%)' }} />

        <motion.div
          variants={sectionVariants}
          initial="initial"
          whileInView="animate"
          viewport={{ once: false, amount: 0.45 }}
          transition={{ duration: 0.6 }}
          className="relative z-10 h-full flex items-center"
          onViewportEnter={() => setActiveDemo('research')}
          onViewportLeave={() => setActiveDemo((prev) => (prev === 'research' ? null : prev))}
        >
          <div className="max-w-7xl mx-auto w-full px-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="space-y-6 text-slate-800">
                <h2 className="text-5xl md:text-[3rem] font-display font-bold text-slate-900">
                  模板驱动的投研流水线
                </h2>
                <p className="text-slate-600 leading-relaxed">
                  结构化模板贯穿「选题 → 数据 → 报告」，自动生成估值草稿、图表与风险提示。
                </p>
                <ul className="space-y-3 text-slate-600">
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-sky-400/80" />
                    <span>模板驱动：选题即生成所需参数、模型与报告框架。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-sky-400/80" />
                    <span>教学行情 / 财务样例即可驱动体验，便于演示与评审。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-sky-400/80" />
                    <span>自动生成估值草稿、图表、风险提示，贴合真实投研节奏。</span>
                  </li>
                </ul>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="rounded-2xl bg-white/90 border border-white/70 backdrop-blur-md p-4 shadow-[0_18px_50px_rgba(30,70,140,0.18)]">
                    <div className="text-xs uppercase tracking-[0.35em] text-sky-600/80">Report Snapshot</div>
                    <div className="mt-3 text-sm leading-relaxed text-slate-700">
                      • 摘要：维持 Hold，目标价 215。<br />
                      • 指标：PE 20｜PEG 0.8｜ROE 23%。<br />
                      • 风险：产能、原材料、汇率。
                    </div>
                  </div>
                  <div className="rounded-2xl bg-white/85 border border-white/60 backdrop-blur-md p-4 shadow-[0_18px_50px_rgba(30,70,140,0.15)]">
                    <div className="text-xs uppercase tracking-[0.35em] text-sky-600/80">Model Timeline</div>
                    <ul className="mt-3 text-sm space-y-2 text-slate-700">
                      <li>① 读取模板参数</li>
                      <li>② 注入行情与财务假设</li>
                      <li>③ 输出报告草稿 + 图表</li>
                    </ul>
                  </div>
                </div>
              </div>
              <div>
                <ScenarioDemo script={RESEARCH_DEMO_SCRIPT} accent="blue" isActive={activeDemo === 'research'} />
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Scene 3 – Q&A Engine (Release) */}
      <section className="relative h-screen snap-start overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#f1e9ff] via-[#f5ecff] to-[#ece2ff]" />
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'linear-gradient(140deg, rgba(190,160,255,0.24), transparent 70%), radial-gradient(860px 520px at 38% 44%, rgba(210,190,255,0.22) 0%, transparent 74%)' }} />

        <motion.div
          variants={sectionVariants}
          initial="initial"
          whileInView="animate"
          viewport={{ once: false, amount: 0.45 }}
          transition={{ duration: 0.6 }}
          className="relative z-10 h-full flex items-center"
          onViewportEnter={() => setActiveDemo('companion')}
          onViewportLeave={() => setActiveDemo((prev) => (prev === 'companion' ? null : prev))}
        >
          <div className="max-w-7xl mx-auto w-full px-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="space-y-6 text-slate-800">
                <h2 className="text-5xl md:text-[3rem] font-display font-bold text-slate-900">
                  讲逻辑、给数据的 AI 导师
                </h2>
                <p className="text-slate-600 leading-relaxed">
                  与学习、投研同步的问答助手，用“回答即解释”交付结论、数据与风险建议。
                </p>
                <ul className="space-y-3 text-slate-600">
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-violet-400/80" />
                    <span>场景感知：知道你正在处理哪段流程，回答直接指向当前任务。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-violet-400/80" />
                    <span>输出格式统一包含结论、数据来源、逻辑链与建议动作。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-violet-400/80" />
                    <span>支持多轮追问，保留底稿，方便复盘与知识沉淀。</span>
                  </li>
                </ul>
                <div className="grid grid-cols-3 gap-4 pt-2">
                  {[
                    { label: '响应时间', value: '2.3s' },
                    { label: '实时引用', value: '3 条' },
                    { label: '建议强度', value: '中性偏多' },
                  ].map((metric) => (
                    <div key={metric.label} className="rounded-2xl bg-white/92 border border-white/70 backdrop-blur-md px-4 py-3 text-center shadow-[0_20px_55px_rgba(130,90,220,0.18)]">
                      <div className="text-[0.65rem] uppercase tracking-[0.35em] text-violet-600/80">{metric.label}</div>
                      <div className="mt-2 text-lg font-semibold text-slate-800">{metric.value}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <ScenarioDemo script={COMPANION_DEMO_SCRIPT} accent="violet" isActive={activeDemo === 'companion'} />
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Scene 4 – 已移除（App Ecosystem） */}

      {/* Scene 5 – Interactive Hub (Resonance & Closure) */}
      <section className="relative h-screen snap-start overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#f4f6fb] via-[#edf4f2] to-[#f9f3ff]" />
        <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(980px 540px at 62% 42%, rgba(180,230,220,0.22) 0%, transparent 70%)' }} />

        <motion.div
          variants={sectionVariants}
          initial="initial"
          whileInView="animate"
          viewport={{ once: false, amount: 0.3 }}
          transition={{ duration: 0.7, ease: easeInOutCubic }}
          className="relative z-10 h-full flex items-center"
          onViewportEnter={() => setActiveDemo(null)}
        >
          <div className="max-w-7xl mx-auto w-full px-6">
            <div className="text-center mb-10">
              <h2 className="text-4xl md:text-5xl font-display font-bold text-slate-900">Interactive Hub</h2>
              <p className="mt-4 text-slate-600">作为收束与起点的三卡布局：Learning / Research / Q&A</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { title: 'Learning', desc: '概念 awakening → 任务生成', href: '/learning' },
                { title: 'Research', desc: '结构化模板 → 数据计算', href: '/research' },
                { title: 'Q&A', desc: '逻辑与来源 → 即问即答', href: '/qa' },
              ].map((card, idx) => (
                <motion.div
                  key={card.title}
                  initial={{ opacity: 0, y: 12 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.12 * idx, duration: 0.6, ease: easeInOutCubic }}
                  className="glass-effect-strong rounded-2xl p-6 border border-primary-100 group hover:shadow-[0_0_30px_rgba(42,199,165,0.25)] transition-all"
                >
                  <div className="text-xl font-semibold text-slate-900 mb-2">{card.title}</div>
                  <div className="text-slate-600 mb-6">{card.desc}</div>
                  <button onClick={() => navigate(card.href)} className="px-5 py-2 rounded-xl bg-primary-500 text-white hover:bg-primary-600 transition-colors inline-flex items-center gap-2">
                    Explore
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </motion.div>
              ))}
            </div>

            <motion.div
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.8 }}
              className="mt-10 text-center"
            >
              <MagneticButton className="inline-block">
                <button
                  onClick={() => navigate('/research')}
                  className="px-8 py-4 bg-white/80 backdrop-blur-sm border-2 border-primary-200 text-primary-700 rounded-2xl font-semibold text-lg hover:bg-white/90 hover:border-primary-300 transition-all duration-300"
                >
                  Connect Backend →
                </button>
              </MagneticButton>
            </motion.div>
          </div>
        </motion.div>
      </section>
    </div>
  )
}

export default LandingPage