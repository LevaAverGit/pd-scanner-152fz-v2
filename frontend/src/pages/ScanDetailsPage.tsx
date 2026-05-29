import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getScan } from '../lib/api'
import type { ScanResult } from '../lib/types'
import UrlPreviewCard from '../components/UrlPreviewCard'
import SummaryCards from '../components/SummaryCards'
import RiskBadge from '../components/RiskBadge'
import FieldTable from '../components/FieldTable'
import TimelinePanel from '../components/TimelinePanel'
import SiteSummaryPanel from '../components/SiteSummaryPanel'
import VisitedPagesTable from '../components/VisitedPagesTable'
import VendorInsightsPanel from '../components/VendorInsightsPanel'
import SubmissionTargetsPanel from '../components/SubmissionTargetsPanel'
import PolicyAnalysisPanel from '../components/PolicyAnalysisPanel'
import InteractiveFindingsPanel from '../components/InteractiveFindingsPanel'
import ConsentSignalsPanel from '../components/ConsentSignalsPanel'
import SyntheticSubmissionPanel from '../components/SyntheticSubmissionPanel'
import FZ152AssessmentPanel from '../components/FZ152AssessmentPanel'

const POLL_INTERVAL_MS = 3000
const POLL_TIMEOUT_MS = 60000

export default function ScanDetailsPage() {
  const { scan_id } = useParams<{ scan_id: string }>()
  const [result, setResult] = useState<ScanResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [timedOut, setTimedOut] = useState(false)

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function stopPolling() {
    if (pollRef.current) clearInterval(pollRef.current)
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
  }

  useEffect(() => {
    if (!scan_id) {
      setError('Missing scan ID')
      setLoading(false)
      return
    }

    async function fetchScan() {
      try {
        const data = await getScan(scan_id!)
        setResult(data)
        setLoading(false)
        if (data.status === 'complete' || data.status === 'failed') {
          stopPolling()
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch scan')
        setLoading(false)
        stopPolling()
      }
    }

    void fetchScan()

    pollRef.current = setInterval(() => {
      void fetchScan()
    }, POLL_INTERVAL_MS)

    timeoutRef.current = setTimeout(() => {
      stopPolling()
      setTimedOut(true)
      setLoading(false)
    }, POLL_TIMEOUT_MS)

    return () => stopPolling()
  }, [scan_id])

  const isPolling = result?.status === 'pending' || result?.status === 'processing'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <Link to="/" className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800">
        &larr; Back to Dashboard
      </Link>

      {loading && !result && (
        <div className="flex items-center gap-2 text-gray-500">
          <span className="inline-block h-4 w-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          <span className="text-sm">Loading scan...</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700 font-medium">Error: {error}</p>
        </div>
      )}

      {timedOut && !error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-700 font-medium">
            Scan timed out — the backend has not returned a final status after 60 seconds.
            You can refresh the page to check again.
          </p>
        </div>
      )}

      {isPolling && result && (
        <div className="flex items-center gap-2 text-blue-600">
          <span className="inline-block h-4 w-4 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          <span className="text-sm">
            {result.status === 'processing' ? 'Scan in progress...' : 'Waiting to start...'}
          </span>
        </div>
      )}

      {result && (
        <>
          {result.status === 'failed' && result.error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-sm font-semibold text-red-700 mb-1">Scan failed</p>
              <p className="text-sm text-red-600">{result.error}</p>
            </div>
          )}

          <UrlPreviewCard result={result} />

          {result.status === 'complete' && (
            <>
              <SummaryCards result={result} />

              {/* Aggregated data categories */}
              <div className="bg-white border rounded-lg p-4">
                <div className="flex items-center gap-3 mb-4">
                  <h2 className="text-base font-semibold text-gray-900">Overall Risk</h2>
                  <RiskBadge categories={result.data_categories} />
                </div>
                <h3 className="text-sm font-medium text-gray-700 mb-3">
                  Data Categories
                  {result.visited_pages.length > 1 && (
                    <span className="ml-1 font-normal text-gray-400">
                      (aggregated across {result.visited_pages.length} pages)
                    </span>
                  )}
                </h3>
                <FieldTable categories={result.data_categories} />
              </div>

              {/* Site crawl summary — shown when crawl data is present */}
              {result.site_summary && <SiteSummaryPanel result={result} />}

              {/* Policy / privacy page analysis */}
              {result.policy_analysis && (
                <PolicyAnalysisPanel analysis={result.policy_analysis} />
              )}

              {/* Interactive discovery findings */}
              <InteractiveFindingsPanel pages={result.visited_pages} />

              {/* Consent signals */}
              <ConsentSignalsPanel pages={result.visited_pages} />

              {/* 152-FZ evidence layer */}
              {result.fz152_assessment && (
                <FZ152AssessmentPanel
                  assessment={result.fz152_assessment}
                  operatorMetadata={result.operator_metadata}
                />
              )}

              {/* Synthetic submission results */}
              <SyntheticSubmissionPanel result={result} />

              {/* Form submission analysis */}
              <SubmissionTargetsPanel pages={result.visited_pages} />

              {/* Vendor / third-party ecosystem */}
              {result.vendor_summary && result.vendor_summary.length > 0 && (
                <VendorInsightsPanel vendors={result.vendor_summary} />
              )}

              {/* Per-page breakdown */}
              {result.visited_pages.length > 0 && (
                <div className="bg-white border rounded-lg p-4">
                  <h2 className="text-base font-semibold text-gray-900 mb-3">
                    Pages Visited
                    <span className="ml-2 text-sm font-normal text-gray-400">
                      ({result.visited_pages.length}{' '}
                      {result.visited_pages.length === 1 ? 'page' : 'pages'})
                    </span>
                  </h2>
                  <VisitedPagesTable pages={result.visited_pages} />
                </div>
              )}

              {/* Network observations */}
              <div className="bg-white border rounded-lg p-4">
                <h2 className="text-base font-semibold text-gray-900 mb-3">
                  Network Observations
                </h2>
                {result.network_observations.length === 0 ? (
                  <p className="text-sm text-gray-500">No network observations.</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                          <th className="px-4 py-2 font-medium">Host</th>
                          <th className="px-4 py-2 font-medium">Type</th>
                          <th className="px-4 py-2 font-medium">Method</th>
                          <th className="px-4 py-2 font-medium">Party</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {result.network_observations.map((obs, i) => (
                          <tr key={i} className={i % 2 === 1 ? 'bg-gray-50' : 'bg-white'}>
                            <td className="px-4 py-2 font-mono text-xs text-gray-700 break-all">
                              {obs.host}
                            </td>
                            <td className="px-4 py-2 text-gray-600">{obs.resource_type}</td>
                            <td className="px-4 py-2 text-gray-600">{obs.method}</td>
                            <td className="px-4 py-2">
                              {obs.is_third_party ? (
                                <span className="text-amber-600 font-medium">Third-party</span>
                              ) : (
                                <span className="text-gray-400">First-party</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {(result.raw_json_export_path || result.markdown_export_path) && (
                <div className="bg-white border rounded-lg p-4">
                  <h2 className="text-base font-semibold text-gray-900 mb-3">Export</h2>
                  <div className="flex items-center gap-4">
                    {result.raw_json_export_path && (
                      <a
                        href={`/${result.raw_json_export_path}`}
                        download
                        className="inline-flex items-center px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-md"
                      >
                        Download JSON
                      </a>
                    )}
                    {result.markdown_export_path && (
                      <a
                        href={`/${result.markdown_export_path}`}
                        download
                        className="inline-flex items-center px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-md"
                      >
                        Download Markdown
                      </a>
                    )}
                  </div>
                </div>
              )}
            </>
          )}

          <div className="bg-white border rounded-lg p-4">
            <h2 className="text-base font-semibold text-gray-900 mb-3">Timeline</h2>
            <TimelinePanel result={result} />
          </div>
        </>
      )}
    </div>
  )
}
