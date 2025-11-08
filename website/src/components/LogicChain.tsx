import React from 'react'
import { motion } from 'framer-motion'

type Node = { id: string; label: string }

const sample: Node[] = [
  { id: 'n1', label: '数据抓取' },
  { id: 'n2', label: '特征计算' },
  { id: 'n3', label: '估值模型' },
  { id: 'n4', label: '结论/建议' },
]

type LogicChainProps = {
  nodes?: Node[]
}

const LogicChain: React.FC<LogicChainProps> = ({ nodes = sample }) => {
  return (
    <div className="w-full rounded-2xl bg-white/80 border border-primary-100 p-6">
      <div className="text-slate-700 font-medium mb-4">逻辑链路</div>
      <div className="flex items-center justify-between gap-3">
        {nodes.map((n, idx) => (
          <React.Fragment key={n.id}>
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.12 }}
              className="px-3 py-2 rounded-xl bg-primary-50 border border-primary-100 text-primary-700 text-sm"
            >
              {n.label}
            </motion.div>
            {idx < nodes.length - 1 && (
              <motion.div
                initial={{ scaleX: 0, opacity: 0 }}
                animate={{ scaleX: 1, opacity: 1 }}
                transition={{ delay: idx * 0.12 + 0.06 }}
                className="h-px flex-1 bg-gradient-to-r from-primary-200 to-primary-400"
                style={{ transformOrigin: 'left' }}
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}

export default LogicChain