import type { DataCategoryItem } from '../lib/types'
import { HIGH_RISK_CATEGORIES } from '../lib/utils'

interface Props {
  categories: DataCategoryItem[]
}

export default function RiskBadge({ categories }: Props) {
  const highRiskCount = categories.filter(c =>
    HIGH_RISK_CATEGORIES.has(c.category)
  ).length

  let label: string
  let colorClass: string

  if (highRiskCount === 0) {
    label = 'Low Risk'
    colorClass = 'bg-green-100 text-green-700'
  } else if (highRiskCount <= 2) {
    label = 'Medium Risk'
    colorClass = 'bg-yellow-100 text-yellow-700'
  } else {
    label = 'High Risk'
    colorClass = 'bg-red-100 text-red-700'
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  )
}
