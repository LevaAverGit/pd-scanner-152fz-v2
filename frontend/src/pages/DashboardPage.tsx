import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import ScanForm from '../components/ScanForm'
import { getHistory, deleteHistoryItem } from '../lib/api'
import type { HistoryItem } from '../lib/types'
import { formatDate, statusColor } from '../lib/utils'
import { Link } from 'react-router-dom'

export default function DashboardPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const loadHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getHistory(20, 0)
      setItems(data.items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadHistory()
  }, [loadHistory])

  function handleScanStarted(scanId: string) {
    navigate(`/scan/${scanId}`)
  }

  async function handleDelete(scanId: string) {
    setDeletingId(scanId)
    try {
      await deleteHistoryItem(scanId)
      await loadHistory()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete scan')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-4">Scan a Page</h1>
        <ScanForm onScanStarted={handleScanStarted} />
      </div>

      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Scans</h2>

        {loading && (
          <p className="text-sm text-gray-500">Loading...</p>
        )}

        {error && !loading && (
          <p className="text-sm text-red-600">{error}</p>
        )}

        {!loading && !error && items.length === 0 && (
          <p className="text-sm text-gray-500">
            No scans yet. Enter a URL above to get started.
          </p>
        )}

        {!loading && items.length > 0 && (
          <div className="bg-white border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide border-b">
                  <th className="px-4 py-3 font-medium">URL</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Date</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {items.map(item => (
                  <tr key={item.scan_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 max-w-xs">
                      <span className="truncate block text-gray-700 font-mono text-xs">
                        {item.url}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${statusColor(item.status)}`}
                      >
                        {item.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-gray-500">
                      {formatDate(item.created_at)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-3">
                        <Link
                          to={`/scan/${item.scan_id}`}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          View
                        </Link>
                        <button
                          onClick={() => void handleDelete(item.scan_id)}
                          disabled={deletingId === item.scan_id}
                          className="text-red-500 hover:text-red-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {deletingId === item.scan_id ? 'Deleting...' : 'Delete'}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
