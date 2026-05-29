import type { ScanResult } from '../lib/types'

interface Props {
  result: ScanResult
}

export default function UrlPreviewCard({ result }: Props) {
  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <div>
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Scanned URL</p>
        <p className="text-sm text-gray-900 break-all font-mono">{result.url}</p>
      </div>

      {result.screenshot_path ? (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Screenshot</p>
          <img
            src={`/${result.screenshot_path}`}
            alt="Page screenshot"
            className="max-h-64 w-auto rounded border object-top"
          />
        </div>
      ) : (
        <div className="flex items-center justify-center h-32 bg-gray-100 rounded border">
          <p className="text-sm text-gray-400">No screenshot available</p>
        </div>
      )}
    </div>
  )
}
