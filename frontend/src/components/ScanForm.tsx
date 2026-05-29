import { useState } from 'react'
import { postScan } from '../lib/api'

interface Props {
  onScanStarted: (scanId: string) => void
}

export default function ScanForm({ onScanStarted }: Props) {
  const [url, setUrl] = useState('')
  const [notes, setNotes] = useState('')
  const [showNotes, setShowNotes] = useState(false)
  const [loading, setLoading] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setValidationError(null)
    setApiError(null)

    const trimmed = url.trim()
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      setValidationError('URL must start with http:// or https://')
      return
    }

    setLoading(true)
    try {
      const result = await postScan(trimmed, notes.trim() || undefined)
      onScanStarted(result.scan_id)
    } catch (err) {
      setApiError(err instanceof Error ? err.message : 'Unexpected error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white border rounded-lg p-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="scan-url" className="block text-sm font-medium text-gray-700 mb-1">
            URL to scan
          </label>
          <input
            id="scan-url"
            type="text"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://example.com/register"
            disabled={loading}
            className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
          />
          {validationError && (
            <p className="mt-1 text-xs text-red-600">{validationError}</p>
          )}
        </div>

        <div>
          <button
            type="button"
            onClick={() => setShowNotes(v => !v)}
            className="text-xs text-gray-500 hover:text-gray-700 underline"
          >
            {showNotes ? 'Hide notes' : 'Add notes (optional)'}
          </button>
          {showNotes && (
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Optional notes about this scan..."
              rows={3}
              disabled={loading}
              className="mt-2 w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            />
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? 'Scanning...' : 'Scan'}
        </button>

        {apiError && (
          <p className="text-sm text-red-600 mt-2">{apiError}</p>
        )}
      </form>

      <p className="mt-4 text-xs text-gray-400 leading-relaxed">
        This tool only analyses pages you explicitly provide. It does not submit forms, bypass
        protections, or store data outside this machine.
      </p>
    </div>
  )
}
