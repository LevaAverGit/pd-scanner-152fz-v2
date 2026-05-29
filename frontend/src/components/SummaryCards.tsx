import type { ReactNode } from 'react'
import type { ScanResult } from '../lib/types'
import { statusColor, relevanceLabel } from '../lib/utils'

interface Props {
  result: ScanResult
}

interface CardProps {
  label: string
  children: ReactNode
}

function Card({ label, children }: CardProps) {
  return (
    <div className="bg-white border rounded-lg p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">{label}</p>
      <div className="text-lg font-bold text-gray-900">{children}</div>
    </div>
  )
}

export default function SummaryCards({ result }: Props) {
  const thirdPartyCount = result.network_observations.filter(o => o.is_third_party).length

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <Card label="Status">
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(result.status)}`}
        >
          {result.status}
        </span>
      </Card>

      <Card label="Form Type">
        <span className="text-base font-semibold">
          {relevanceLabel(result.registration_relevance)}
        </span>
      </Card>

      <Card label="Data Categories Found">
        {result.data_categories.length}
      </Card>

      <Card label="Third-party Hosts">
        {thirdPartyCount}
      </Card>
    </div>
  )
}
