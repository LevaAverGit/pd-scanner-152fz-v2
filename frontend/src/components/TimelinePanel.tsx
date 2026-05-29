import type { ScanResult } from '../lib/types'
import { formatDate } from '../lib/utils'

interface Props {
  result: ScanResult
}

interface TimelineEntryProps {
  label: string
  timestamp: string
  error?: boolean
}

function TimelineEntry({ label, timestamp, error = false }: TimelineEntryProps) {
  return (
    <div className="flex items-start gap-3">
      <div className={`mt-1.5 h-2 w-2 rounded-full flex-shrink-0 ${error ? 'bg-red-400' : 'bg-gray-400'}`} />
      <div>
        <p className={`text-sm ${error ? 'text-red-600 font-medium' : 'text-gray-700'}`}>{label}</p>
        <p className="text-xs text-gray-400">{timestamp}</p>
      </div>
    </div>
  )
}

export default function TimelinePanel({ result }: Props) {
  return (
    <div className="space-y-3">
      <TimelineEntry label="Scan created" timestamp={formatDate(result.created_at)} />
      {result.completed_at && (
        <TimelineEntry label="Scan completed" timestamp={formatDate(result.completed_at)} />
      )}
      {result.error && (
        <TimelineEntry label={`Error: ${result.error}`} timestamp="" error />
      )}
    </div>
  )
}
