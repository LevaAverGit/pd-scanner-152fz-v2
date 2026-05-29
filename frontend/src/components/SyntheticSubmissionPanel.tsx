import { useState } from 'react'
import type { ScanResult, VisitedPageItem } from '../lib/types'

interface Props {
  result: ScanResult
}

function statusBadge(status: string) {
  switch (status) {
    case 'submitted':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
          submitted
        </span>
      )
    case 'blocked':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200">
          blocked
        </span>
      )
    case 'validation_failed':
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-200">
          validation failed
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200">
          {status}
        </span>
      )
  }
}

function truncate(s: string | null, max = 60): string {
  if (!s) return '—'
  return s.length > max ? s.slice(0, max) + '…' : s
}

interface EvidenceRowProps {
  page: VisitedPageItem
}

function EvidenceRow({ page }: EvidenceRowProps) {
  const [open, setOpen] = useState(false)
  const hasEvidence = page.observed_submission_evidence.length > 0

  return (
    <div>
      {hasEvidence && (
        <div className="mt-1">
          <button
            className="text-xs text-blue-600 hover:underline focus:outline-none"
            onClick={() => setOpen(v => !v)}
          >
            {open ? 'Hide' : 'Show'} {page.observed_submission_evidence.length} evidence item
            {page.observed_submission_evidence.length !== 1 ? 's' : ''}
          </button>
          {open && (
            <ul className="mt-1 space-y-0.5 pl-2 border-l-2 border-gray-200">
              {page.observed_submission_evidence.map((ev, i) => (
                <li key={i} className="text-xs text-gray-500 font-mono">
                  {ev}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}

export default function SyntheticSubmissionPanel({ result }: Props) {
  if (!result.synthetic_submission_enabled) return null

  const summary = result.synthetic_submission_summary
  const submittedPages = result.visited_pages.filter(
    p => p.synthetic_submission_attempted && p.synthetic_submission_status !== 'not_attempted'
  )
  const pagesWithFollowOn = result.visited_pages.filter(
    p => p.observed_follow_on_hosts.length > 0
  )

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">Synthetic Submission Mode</h2>
        <span className="text-xs text-gray-400 italic">experimental — requires manual validation</span>
      </div>

      {/* Warning box */}
      <div className="bg-amber-50 border border-amber-200 rounded p-3">
        <p className="text-sm font-medium text-amber-800 mb-1">Synthetic submission was active</p>
        <p className="text-xs text-amber-700">
          Only clearly synthetic placeholder values were used. No real personal data was submitted.
          Inferred downstream routing requires manual validation.
        </p>
      </div>

      {/* Summary stats */}
      {summary && (
        <div className="grid grid-cols-5 gap-2">
          <div className="bg-gray-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-gray-800">{summary.pages_attempted}</p>
            <p className="text-xs text-gray-500 mt-0.5">Pages attempted</p>
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-green-700">{summary.successful_submissions}</p>
            <p className="text-xs text-gray-500 mt-0.5">Successful</p>
          </div>
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-blue-700">{summary.first_party_submissions}</p>
            <p className="text-xs text-gray-500 mt-0.5">First-party</p>
          </div>
          <div className="bg-amber-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-amber-700">{summary.third_party_submissions}</p>
            <p className="text-xs text-gray-500 mt-0.5">Third-party</p>
          </div>
          <div className="bg-red-50 rounded-lg p-3 text-center">
            <p className="text-xl font-bold text-red-700">{summary.blocked_or_failed}</p>
            <p className="text-xs text-gray-500 mt-0.5">Blocked / failed</p>
          </div>
        </div>
      )}

      {/* Submitted pages table */}
      {submittedPages.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Submission Attempts</h3>
          <div className="overflow-x-auto rounded border border-gray-100">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                  <th className="px-3 py-2 font-medium">Page URL</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Method</th>
                  <th className="px-3 py-2 font-medium">Submit URL</th>
                  <th className="px-3 py-2 font-medium">Target Type</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {submittedPages.map((page, i) => (
                  <tr key={i} className={i % 2 === 1 ? 'bg-gray-50' : 'bg-white'}>
                    <td className="px-3 py-2 align-top">
                      <p className="font-mono text-xs text-gray-700 break-all">
                        {truncate(page.url, 55)}
                      </p>
                      <EvidenceRow page={page} />
                    </td>
                    <td className="px-3 py-2 align-top">
                      {statusBadge(page.synthetic_submission_status)}
                    </td>
                    <td className="px-3 py-2 align-top text-xs text-gray-600 font-mono">
                      {page.observed_submit_method ?? '—'}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <span
                        className="font-mono text-xs text-gray-700 break-all"
                        title={page.observed_submit_url ?? undefined}
                      >
                        {truncate(page.observed_submit_url)}
                      </span>
                    </td>
                    <td className="px-3 py-2 align-top">
                      {page.observed_submit_target_type === 'third_party' ? (
                        <span className="text-xs font-medium text-amber-600">third-party</span>
                      ) : page.observed_submit_target_type === 'first_party' ? (
                        <span className="text-xs text-gray-500">first-party</span>
                      ) : (
                        <span className="text-xs text-gray-400">
                          {page.observed_submit_target_type}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {submittedPages.length === 0 && (
        <p className="text-sm text-gray-500">No submission attempts recorded.</p>
      )}

      {/* Follow-on hosts */}
      {pagesWithFollowOn.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Observed Follow-on Hosts</h3>
          <div className="space-y-2">
            {pagesWithFollowOn.map((page, i) => (
              <div key={i} className="rounded border border-gray-100 px-3 py-2">
                <p className="font-mono text-xs text-gray-600 break-all mb-1">{page.url}</p>
                <div className="flex flex-wrap gap-1.5">
                  {page.observed_follow_on_hosts.map((host, j) => (
                    <span
                      key={j}
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-amber-50 text-amber-700 border border-amber-200 font-mono"
                    >
                      {host}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
