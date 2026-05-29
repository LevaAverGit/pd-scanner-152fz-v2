import type { DataCategoryItem } from '../lib/types'
import { confidenceLabel, confidenceColor, HIGH_RISK_CATEGORIES } from '../lib/utils'

interface Props {
  categories: DataCategoryItem[]
}

function capitalize(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export default function FieldTable({ categories }: Props) {
  if (categories.length === 0) {
    return (
      <p className="text-sm text-gray-500 py-4">No personal data categories detected.</p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="px-4 py-2 font-medium">Category</th>
            <th className="px-4 py-2 font-medium">Matched Signals</th>
            <th className="px-4 py-2 font-medium">Confidence</th>
            <th className="px-4 py-2 font-medium">Risk Level</th>
            <th className="px-4 py-2 font-medium">Explanation</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {categories.map((item, i) => {
            const isHighRisk = HIGH_RISK_CATEGORIES.has(item.category)
            return (
              <tr key={item.category} className={i % 2 === 1 ? 'bg-gray-50' : 'bg-white'}>
                <td className="px-4 py-3 whitespace-nowrap">
                  <span className={isHighRisk ? 'font-bold text-gray-900' : 'text-gray-800'}>
                    {capitalize(item.category)}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {item.matched_signals.join(', ') || '—'}
                </td>
                <td className={`px-4 py-3 font-medium ${confidenceColor(item.confidence)}`}>
                  {confidenceLabel(item.confidence)}
                </td>
                <td className="px-4 py-3">
                  {isHighRisk ? (
                    <span className="text-red-600 font-medium">High</span>
                  ) : (
                    <span className="text-gray-400">Standard</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600 max-w-xs">{item.explanation}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
