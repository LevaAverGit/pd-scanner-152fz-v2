import { useState } from 'react'
import type { VisitedPageItem } from '../lib/types'
import { relevanceLabel, relevanceColor } from '../lib/utils'

interface Props {
  pages: VisitedPageItem[]
}

function truncateUrl(url: string, max = 55): string {
  try {
    const { pathname, search } = new URL(url)
    const path = pathname + search
    return path.length > max ? path.slice(0, max) + '…' : path
  } catch {
    return url.length > max ? url.slice(0, max) + '…' : url
  }
}

function ConsentBadges({ page }: { page: VisitedPageItem }) {
  const badges: string[] = []
  if (page.has_privacy_link) badges.push('Privacy')
  if (page.has_terms_link) badges.push('Terms')
  if (page.has_consent_checkbox) badges.push('Consent ✓')
  if (page.has_marketing_consent) badges.push('Mktg ✓')
  if (badges.length === 0) return <span className="text-gray-300">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {badges.map(b => (
        <span
          key={b}
          className="inline-block bg-green-50 border border-green-200 text-green-700 text-xs px-1.5 py-0.5 rounded"
        >
          {b}
        </span>
      ))}
    </div>
  )
}

function ConsentSignalDetail({ page }: { page: VisitedPageItem }) {
  if (page.consent_signals.length === 0) return null
  return (
    <ul className="mt-1 space-y-0.5">
      {page.consent_signals.map((sig, i) => (
        <li key={i} className="text-xs text-gray-500 pl-2 border-l border-green-200">
          {sig}
        </li>
      ))}
    </ul>
  )
}

export default function VisitedPagesTable({ pages }: Props) {
  const [expanded, setExpanded] = useState<number | null>(null)

  if (pages.length === 0) {
    return <p className="text-sm text-gray-500">No pages visited.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
            <th className="px-3 py-2 font-medium w-8">#</th>
            <th className="px-3 py-2 font-medium">URL</th>
            <th className="px-3 py-2 font-medium">Page Type</th>
            <th className="px-3 py-2 font-medium text-center">Forms</th>
            <th className="px-3 py-2 font-medium">Data Found</th>
            <th className="px-3 py-2 font-medium">Consent Signals</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {pages.map((page, i) => {
            const isExpanded = expanded === i
            const hasDetails =
              page.consent_signals.length > 0 ||
              page.notes.length > 0 ||
              page.detected_categories.length > 0

            return (
              <>
                <tr
                  key={i}
                  className={`${i % 2 === 1 ? 'bg-gray-50' : 'bg-white'} ${hasDetails ? 'cursor-pointer hover:bg-blue-50' : ''}`}
                  onClick={() => hasDetails && setExpanded(isExpanded ? null : i)}
                >
                  <td className="px-3 py-2 text-gray-400 text-xs">{i + 1}</td>
                  <td className="px-3 py-2">
                    <a
                      href={page.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-mono text-xs text-blue-600 hover:text-blue-800 break-all"
                      onClick={e => e.stopPropagation()}
                    >
                      {truncateUrl(page.url)}
                    </a>
                    {page.page_title && (
                      <p className="text-xs text-gray-400 mt-0.5 truncate max-w-xs">
                        {page.page_title}
                      </p>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {page.registration_relevance ? (
                      <span
                        className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${relevanceColor(page.registration_relevance)}`}
                      >
                        {relevanceLabel(page.registration_relevance)}
                      </span>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center text-gray-700">
                    {page.forms_found > 0 ? (
                      <span className="font-medium">{page.forms_found}</span>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    {page.detected_categories.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {page.detected_categories.map(c => (
                          <span
                            key={c.category}
                            className="inline-block bg-blue-50 text-blue-700 text-xs px-1.5 py-0.5 rounded"
                          >
                            {c.category}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-300 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <ConsentBadges page={page} />
                  </td>
                </tr>

                {isExpanded && hasDetails && (
                  <tr key={`${i}-detail`} className="bg-blue-50">
                    <td />
                    <td colSpan={5} className="px-3 py-2 pb-3">
                      {page.consent_signals.length > 0 && (
                        <div className="mb-2">
                          <p className="text-xs font-medium text-gray-600 mb-1">
                            Consent signal evidence:
                          </p>
                          <ConsentSignalDetail page={page} />
                        </div>
                      )}
                      {page.detected_categories.length > 0 && (
                        <div className="mb-2">
                          <p className="text-xs font-medium text-gray-600 mb-1">
                            Data categories ({page.fields_count} fields extracted):
                          </p>
                          {page.detected_categories.map(c => (
                            <p key={c.category} className="text-xs text-gray-500 pl-2 border-l border-blue-200">
                              <span className="font-medium">{c.category}</span> — {c.explanation}
                            </p>
                          ))}
                        </div>
                      )}
                      {page.notes.length > 0 && (
                        <div>
                          <p className="text-xs font-medium text-gray-600 mb-1">Notes:</p>
                          {page.notes.map((n, ni) => (
                            <p key={ni} className="text-xs text-gray-500 pl-2 border-l border-gray-200">{n}</p>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </>
            )
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-gray-400">
        Click a row to expand per-page detail. Consent signals are heuristic indicators only.
      </p>
    </div>
  )
}
