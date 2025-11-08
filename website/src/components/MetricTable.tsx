import React from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'

type Row = {
  label: string
  value: string
  change?: number // positive for up, negative for down
}

const sample: Row[] = [
  { label: 'PE (TTM)', value: '20.1', change: 0.6 },
  { label: 'EPS', value: '10.0', change: 0.0 },
  { label: '行业均值PE', value: '15.0', change: -0.2 },
  { label: '市值', value: '¥ 6,000 亿', change: 0.4 },
]

type MetricTableProps = {
  rows?: Row[]
}

const MetricTable: React.FC<MetricTableProps> = ({ rows = sample }) => {
  return (
    <div className="w-full rounded-2xl bg-white/80 border border-primary-100 overflow-hidden">
      <div className="px-4 py-3 bg-gradient-to-r from-primary-50 to-white text-slate-700 font-medium">指标速览</div>
      <div className="divide-y divide-primary-100">
        {rows.map((r) => (
          <div key={r.label} className="px-4 py-3 flex items-center justify-between">
            <div className="text-slate-700">{r.label}</div>
            <div className="flex items-center gap-3">
              <span className="font-semibold text-slate-900">{r.value}</span>
              {typeof r.change === 'number' && r.change !== 0 && (
                <span className={`inline-flex items-center gap-1 text-sm ${r.change > 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                  {r.change > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                  {Math.abs(r.change).toFixed(1)}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default MetricTable