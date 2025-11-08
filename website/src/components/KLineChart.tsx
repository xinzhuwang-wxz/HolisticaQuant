import React from 'react'
import { motion } from 'framer-motion'

type Candle = { time: string; open: number; close: number; high: number; low: number }

const sample: Candle[] = [
  { time: '09:30', open: 100, close: 104, high: 106, low: 99 },
  { time: '10:00', open: 104, close: 101, high: 105, low: 100 },
  { time: '10:30', open: 101, close: 108, high: 112, low: 100 },
  { time: '11:00', open: 108, close: 107, high: 110, low: 106 },
  { time: '13:00', open: 107, close: 112, high: 114, low: 106 },
  { time: '14:00', open: 112, close: 110, high: 113, low: 109 },
  { time: '15:00', open: 110, close: 116, high: 118, low: 109 },
]

type KLineChartProps = {
  data?: Candle[]
  width?: number
  height?: number
}

/**
 * 轻量级K线图SVG：用于场景页的拟真金融组件展示。
 */
const KLineChart: React.FC<KLineChartProps> = ({ data = sample, width = 520, height = 240 }) => {
  const padding = 20
  const bodyW = width - padding * 2
  const bodyH = height - padding * 2
  const values = data.flatMap(d => [d.open, d.close, d.high, d.low])
  const min = Math.min(...values)
  const max = Math.max(...values)
  const toY = (v: number) => padding + bodyH - ((v - min) / (max - min)) * bodyH
  const step = bodyW / data.length

  return (
    <motion.svg
      width={width}
      height={height}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
    >
      <defs>
        <linearGradient id="kline-bg" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="rgba(42,199,165,0.20)" />
          <stop offset="100%" stopColor="rgba(42,199,165,0.03)" />
        </linearGradient>
      </defs>
      <rect x={0} y={0} width={width} height={height} rx={16} fill="url(#kline-bg)" />
      {/* grid */}
      {[0, 1, 2, 3].map(i => (
        <line key={i} x1={padding} x2={width - padding} y1={padding + (bodyH / 3) * i} y2={padding + (bodyH / 3) * i} stroke="rgba(255,255,255,0.2)" strokeWidth={0.6} />
      ))}
      {/* candles */}
      {data.map((d, i) => {
        const x = padding + i * step + step / 2
        const color = d.close >= d.open ? '#22c55e' : '#ef4444'
        const yHigh = toY(d.high)
        const yLow = toY(d.low)
        const yOpen = toY(d.open)
        const yClose = toY(d.close)
        const rectY = Math.min(yOpen, yClose)
        const rectH = Math.abs(yClose - yOpen) || 2
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={yHigh} y2={yLow} stroke={color} strokeWidth={2} />
            <rect x={x - step * 0.18} y={rectY} width={step * 0.36} height={rectH} fill={color} rx={2} />
          </g>
        )
      })}
    </motion.svg>
  )
}

export default KLineChart