import React, { useCallback, useEffect, useState } from 'react'
import { motion, useAnimation } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, ChevronDown, Github } from 'lucide-react'

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
  const [showNav, setShowNav] = useState(false)
  const [showScrollHint, setShowScrollHint] = useState(false)
  const quickLinks = [
    {
      label: 'Learning',
      onClick: () => handleScrollTo('scene-learning'),
      accent: 'from-white/35 via-white/18 to-white/6 text-white/85 hover:text-white',
    },
    {
      label: 'Research',
      onClick: () => handleScrollTo('scene-research'),
      accent: 'from-white/35 via-white/18 to-white/6 text-white/85 hover:text-white',
    },
    {
      label: 'Q&A',
      onClick: () => handleScrollTo('scene-qa'),
      accent: 'from-white/35 via-white/18 to-white/6 text-white/85 hover:text-white',
    },
    {
      label: 'Start Experience',
      onClick: () => handleScrollTo('experience'),
      accent: 'from-primary-400/65 via-primary-500/55 to-primary-500/40 text-white hover:text-white',
    },
  ]

  const handleScrollTo = useCallback((targetId: string) => {
    const target = document.getElementById(targetId)
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [])

  const titleLayout = [
    { letters: 'Holistica'.split(''), anchorIndex: 4 },
    { letters: 'Quant'.split(''), anchorIndex: 2 },
  ]

  const lettersAppearDelay = (layout: typeof titleLayout) => {
    return layout.reduce((maxDelay, { letters, anchorIndex }, lineIdx) => {
      const lineDelay = lineIdx * 0.5
      const maxOffset = letters.reduce((acc, _, idx) => Math.max(acc, Math.abs(anchorIndex - idx)), 0)
      const letterDelay = maxOffset * 0.18
      return Math.max(maxDelay, lineDelay + letterDelay)
    }, 0)
  }

  const letterVariants = {
    hidden: (custom: { offset: number }) => ({
      opacity: 0,
      x: (custom?.offset ?? 0) * 22,
      y: 12,
      scale: 0.98,
    }),
    visible: (custom: { offset: number }) => ({
      opacity: 1,
      x: 0,
      y: 0,
      scale: 1,
      transition: {
        duration: 2.2,
        ease: easeInOutCubic,
        delay: Math.abs(custom?.offset ?? 0) * 0.18,
      },
    }),
  }

  const lineVariants = {
    hidden: { opacity: 0 },
    visible: (custom: { lineIdx: number }) => ({
      opacity: 1,
      transition: {
        delayChildren: (custom?.lineIdx ?? 0) * 0.32,
        staggerChildren: 0.04,
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
    { role: 'user', content: '🔍 老师，我看到数字人民币扩围了，银行真的会赚更多吗？' },
    {
      role: 'assistant',
      content:
        '🌐 好敏锐！先看真实指标：2025 年 11 个试点城市、1.1 亿钱包、2.8 亿笔交易。想像你是数字化主管，第一反应会盯哪个指标？',
    },
    { role: 'user', content: '我会抓收入，看看试点前后差多少。' },
    {
      role: 'assistant',
      content:
        '🧮 正中靶心！试点前收入 10 亿，试点后 12 亿——增长率 = (12−10)/10 = **20%**。你觉得这个 20% 更像是渗透还是效率？',
    },
    { role: 'user', content: '渗透率吧，感觉更多人用了。' },
    {
      role: 'assistant',
      content:
        '✨ 你嗅到重点了！我们来个小实验：换个设定——钱包用户翻倍，但交易频次掉 20%。我们一起算看看。',
    },
    { role: 'user', content: '好呀，我猜增速会掉。' },
    {
      role: 'assistant',
      content:
        '🧠 模拟结果：增长率降到 **12%**。发现了吗？要跑赢市场，要同时提渗透、守活跃。最后，我们用财报数据验证：银行 2025Q1 数字化收入同比 +19%~22%，刚好在你推的区间。',
    },
    {
      role: 'note',
      content:
        '✅ 小结：带着问题进场 → 换变量做实验 → 拿官方数据作证。Learning Studio 会把这套推理完整记到学习卡里。',
    },
  ]

  const RESEARCH_DEMO_SCRIPT: DemoEntry[] = [
    {
      role: 'user',
      content: '💡 想跑一下宁德时代的估值模板，看看现在价位到底稳不稳？',
    },
    {
      role: 'assistant',
      content:
        '📈 好的！调用「公司估值报告」模板，加载最新 A 股指标：股价 180 元、EPS 6.8、行业 PE 24。你想先看估值对比还是做敏感性？',
    },
    {
      role: 'user',
      content: '先算当前 PE，再把利润增速调到 18%，感受一下安全边际。',
    },
    {
      role: 'assistant',
      content:
        '🧮 当前 PE ≈ 26，比行业 24 略贵。利润增速降到 18% 时，PEG 拉到 1.4，安全边际明显收窄。要不要顺手看下储能业务翻倍后的上行空间？',
    },
    {
      role: 'user',
      content: '好呀，顺便看看行业雷达里算力渗透率的对比。',
    },
    {
      role: 'assistant',
      content:
        '🔍 更新假设后模型给出目标价 205~215 元，行业雷达提示储能渗透率带来 15% 上行，风险雷达则把锂价、海外交付列为监控重点。要不要顺便生成敏感性矩阵？',
    },
    {
      role: 'user',
      content: '当然，做成投委会底稿最合适。',
    },
    {
      role: 'note',
      content: '✅ 模板拉通 → 变量实验 → 风险验证。估值草稿 + 敏感性矩阵 + 监控清单一键导出，投研小组直接接力。',
    },
  ]

  const COMPANION_DEMO_SCRIPT: DemoEntry[] = [
    { role: 'user', content: '🧭 晨会要复盘国产 AI 服务器，先把示例流程播一遍？' },
    {
      role: 'assistant',
      content:
        '🎬 示例模式启动：① 行业逻辑（IDC 2025H1）② 资金信号（板块净流 +4%）③ 风险提示（锂价 & 交付）。流式字幕马上播。',
    },
    {
      role: 'user', content: '客户刚问“今年毛利会不会被压扁”，能直接接到这条线上吗？' },
    {
      role: 'assistant',
      content:
        '🔁 已切到自定义轨道：加节点「采集毛利历史 → 引用厂商指引 → 输出监控指标」。保持同一 timeline，不丢上下文。',
    },
    { role: 'user', content: '每段播的时候把引用也念出来，投委会要看出处。' },
    {
      role: 'assistant',
      content:
        '📡 Timeline 正在播：工信部《算力白皮书 2025H1》、两家厂商 2025Q2 财报、IDC 预测。结论：毛利或压缩 1~1.5pct，可用服务化对冲，行动清单已同步。',
    },
    {
      role: 'note',
      content:
        '✅ 示例速览 → 自定义追问 → 流式旁白 + 引用回放。问答结束即得到回答草稿、引用列表与动作清单。',
    },
  ]

  useEffect(() => {
    let navTimer: ReturnType<typeof setTimeout> | undefined
    let hintTimer: ReturnType<typeof setTimeout> | undefined

    const runSequence = async () => {
      setShowNav(false)
      setShowScrollHint(false)
      await titleControls.start('visible')
      setBreathing(true)
      setActiveDemo('learning')
      navTimer = setTimeout(() => setShowNav(true), 80)
      hintTimer = setTimeout(() => setShowScrollHint(true), 340)
    }

    runSequence()

    return () => {
      if (navTimer) clearTimeout(navTimer)
      if (hintTimer) clearTimeout(hintTimer)
    }
  }, [titleControls])

  return (
    <div className="h-screen w-screen overflow-y-scroll snap-y snap-mandatory bg-gradient-to-br from-slate-50 via-white to-cyan-50/30">
      {/* Hero Section – Cinematic Brand Entry */}
      <section id="hero" className="relative h-screen snap-start overflow-hidden">
        {/* Atmospheric background */}
        <div className="absolute inset-0 noise-bg" />
        <div className="absolute inset-0 bg-gradient-to-br from-[#0A1A2F] via-[#0F2744] to-cyan-600/20" />
        {/* Cinematic fog intro */}
        <motion.div
          className="absolute inset-0 pointer-events-none bg-gradient-to-br from-[#040910] via-[#09172A] to-[#123456]"
          initial={{ opacity: 0.35 }}
          animate={{ opacity: [0.35, 0.3, 0.22, 0.14, 0.08] }}
          transition={{ duration: 3.6, ease: easeInOutCubic }}
        />
        <div
          className="absolute inset-0 pointer-events-none"
          style={{ background: 'radial-gradient(1200px 650px at 50% 45%, rgba(42,199,165,0.2) 0%, rgba(42,199,165,0.08) 40%, transparent 72%)', opacity: 0.26 }}
        />
        <div
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(closest-side, rgba(255,255,255,0.42), rgba(255,255,255,0) 70%)',
            filter: 'blur(60px)',
            opacity: 0.2
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
          {/* Frosted quick navigation */}
          {showNav && (
            <motion.nav
              className="absolute top-8 left-8 z-20 hidden md:block"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: easeInOutCubic }}
            >
              <div className="flex flex-wrap gap-2.5">
                {quickLinks.map((item, index) => (
                  <motion.button
                    key={item.label}
                    onClick={item.onClick}
                    className={`px-5 py-2.5 rounded-lg bg-gradient-to-br ${item.accent} shadow-[0_8px_26px_rgba(6,20,38,0.24)] text-[0.7rem] font-medium tracking-[0.12em] capitalize transition-all duration-300 hover:shadow-[0_12px_36px_rgba(14,38,70,0.3)] hover:-translate-y-[2px]`}
                    style={{ backdropFilter: 'blur(10px)' }}
                    initial={{ opacity: 0, y: -6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.06, duration: 0.24, ease: easeInOutCubic }}
                  >
                    {item.label}
                  </motion.button>
                ))}
              </div>
            </motion.nav>
          )}
          {showNav && (
            <motion.a
              href="https://github.com/xinzhuwang-wxz/HolisticaQuant"
              target="_blank"
              rel="noopener noreferrer"
              className="absolute top-5 right-12 z-20 hidden md:flex items-center justify-center rounded-full w-10 h-10 bg-white/12 shadow-[0_8px_24px_rgba(6,20,38,0.24)] text-white hover:bg-white/18 transition-colors"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: easeInOutCubic, delay: quickLinks.length * 0.06 }}
              style={{ backdropFilter: 'blur(10px)' }}
            >
              <Github className="w-5 h-5" />
            </motion.a>
          )}

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
                  style={
                    lineIdx === 1
                      ? { transform: 'translateX(-0.5rem)' }
                      : { transform: 'translateX(0)' }
                  }
                >
                  {letters.map((char, charIdx) => (
                    <motion.span
                      key={`char-${lineIdx}-${charIdx}`}
                      variants={letterVariants}
                      custom={{ offset: anchorIndex - charIdx }}
                      className="text-transparent bg-clip-text"
                      style={{
                        backgroundImage: 'linear-gradient(135deg, rgba(255,255,255,0.98), rgba(163,250,226,0.9) 35%, rgba(42,199,165,0.82) 70%, rgba(25,50,84,0.95))',
                        textShadow: '0 35px 100px rgba(8,18,32,0.68), 0 18px 52px rgba(42,199,165,0.5), 0 0 22px rgba(255,255,255,0.75)',
                        willChange: 'opacity, transform'
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
                    transition: { delay: lettersAppearDelay(titleLayout) + 0.05, duration: 0.5, ease: easeInOutCubic },
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
          {showScrollHint && (
            <motion.div
              className="absolute bottom-10 -translate-x-[72%] text-slate-300"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.36, ease: easeInOutCubic }}
            >
              <div className="flex flex-col items-center">
                <span className="text-sm mb-1">Welcome to Future</span>
                <ChevronDown className="w-6 h-6 animate-bounce" />
              </div>
            </motion.div>
          )}
        </div>
      </section>

        {/* Scene 1 – Learning Studio */}
      <section id="scene-learning" className="relative h-screen snap-start overflow-hidden">
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
                  事件驱动、变量实验、数据验证 —— 一条龙把抽象知识做成可练任务。
                </p>
                <ul className="space-y-2 text-slate-600">
                  <li className="flex items-center gap-4 pl-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-teal-400/80" />
                    <span>事件信号：央行公告 + 行业快报秒变任务蓝图</span>
                  </li>
                  <li className="flex items-center gap-4 pl-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-teal-400/80" />
                    <span>变量实验：调渗透率、调频次，立刻读出驱动因子</span>
                  </li>
                  <li className="flex items-center gap-4 pl-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-teal-400/80" />
                    <span>验证快照：财报区间 + 旁路指标一屏对照</span>
                  </li>
                </ul>
                <div className="grid grid-cols-3 gap-3 pt-2">
                  {[
                    { title: 'STEP 01', desc: '锚定标的与模板' },
                    { title: 'STEP 02', desc: '推演关键变量' },
                    { title: 'STEP 03', desc: '生成验证快照' },
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
      <section id="scene-research" className="relative h-screen snap-start overflow-hidden">
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
                  模板驱动的投研流水线：估值模板、行业雷达、风险雷达像投研小组一样接力出报告。
                </p>
                <ul className="space-y-2 text-slate-600">
                  <li className="flex items-center gap-4 pl-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-sky-400/80" />
                    <span>模板加载：宁德时代 / 中芯国际 / 璞泰来一键套入最新指标</span>
                  </li>
                  <li className="flex items-center gap-4 pl-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-sky-400/80" />
                    <span>变量推演：拖动利润、渗透率，立刻看到敏感性曲线</span>
                  </li>
                  <li className="flex items-center gap-4 pl-2">
                    <span className="h-2.5 w-2.5 rounded-full bg-sky-400/80" />
                    <span>验证快照：财报区间、监管引用与监控清单自动生成</span>
                  </li>
                </ul>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="rounded-2xl bg-white/90 border border-white/70 backdrop-blur-md p-4 shadow-[0_18px_50px_rgba(30,70,140,0.18)]">
                    <div className="text-xs uppercase tracking-[0.35em] text-sky-600/80">Report Snapshot</div>
                    <div className="mt-3 text-sm leading-relaxed text-slate-700">
                      • 摘要：维持增持，目标价 205~215。<br />
                      • 指标：PE 26→24｜PEG 1.4→1.0。<br />
                      • 风险：锂价波动、海外交付、汇率。
                    </div>
                  </div>
                  <div className="rounded-2xl bg-white/85 border border-white/60 backdrop-blur-md p-4 shadow-[0_18px_50px_rgba(30,70,140,0.15)]">
                    <div className="text-xs uppercase tracking-[0.35em] text-sky-600/80">Model Timeline</div>
                    <ul className="mt-3 text-sm space-y-2 text-slate-700">
                      <li>① 读取模板参数</li>
                      <li>② 注入行情与财务假设</li>
                      <li>③ 输出估值草稿 + 风险清单</li>
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
      <section id="scene-qa" className="relative h-screen snap-start overflow-hidden">
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
                  会讲故事的投研对话台
                </h2>
                <p className="text-slate-600 leading-relaxed">
                  同一条对话线里，先播示例、再接追问、最后沉淀行动，一次流式完成复盘。
                </p>
                <ul className="space-y-3 text-slate-600">
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-violet-400/80" />
                    <span>叙事流推演：问题 → 推理 → 行动的旁白节奏，同步展示引用出处。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-violet-400/80" />
                    <span>示例 + 自定义一轨：示例初稿秒出，紧接着把你的追问嵌入同一 timeline。</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="mt-2 h-2 w-2 rounded-full bg-violet-400/80" />
                    <span>底稿即成：回答草稿、引用列表、跟进行动自动归档，方便投委会复盘。</span>
                  </li>
                </ul>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="rounded-2xl bg-white/92 border border-white/70 backdrop-blur-md p-4 shadow-[0_20px_55px_rgba(130,90,220,0.18)]">
                    <div className="text-[0.65rem] uppercase tracking-[0.35em] text-violet-600/80">Answer Snapshot</div>
                    <div className="mt-3 text-sm leading-relaxed text-slate-700">
                      • 结论：AI 服务器毛利压缩 1~1.5pct，可用服务化对冲。<br />
                      • 引用：工信部 2025H1｜中信纪要 2025Q2｜IDC 预测。<br />
                      • 行动：盯 GPU 采购价、服务收入占比与海外交付节奏。
                    </div>
                  </div>
                  <div className="rounded-2xl bg-white/88 border border-white/60 backdrop-blur-md p-4 shadow-[0_18px_50px_rgba(120,80,200,0.16)]">
                    <div className="text-[0.65rem] uppercase tracking-[0.35em] text-violet-600/80">Live Timeline</div>
                    <ul className="mt-3 text-sm space-y-2 text-slate-700">
                      <li>① 提问解析</li>
                      <li>② 播报示例答案</li>
                      <li>③ 接入自定义追问</li>
                      <li>④ 输出行动底稿</li>
                    </ul>
                  </div>
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
      <section id="experience" className="relative h-screen snap-start overflow-hidden">
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
          </div>
        </motion.div>
      </section>
    </div>
  )
}

export default LandingPage