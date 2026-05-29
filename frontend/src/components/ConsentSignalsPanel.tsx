import type { VisitedPageItem } from '../lib/types'

interface Props {
  pages: VisitedPageItem[]
}

interface PageConsentRowProps {
  page: VisitedPageItem
  index: number
}

function PageConsentRow({ page, index }: PageConsentRowProps) {
  const allSignals = [
    ...page.consent_signals,
    ...page.dynamic_consent_signals,
  ]

  return (
    <div className={`px-3 py-2 space-y-1 ${index % 2 === 1 ? 'bg-gray-50' : 'bg-white'}`}>
      <p className="text-xs font-mono text-gray-600 break-all">{page.url}</p>
      <div className="flex flex-wrap gap-1.5">
        {page.has_privacy_link && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-50 text-green-700 border border-green-100">
            Privacy link
          </span>
        )}
        {page.has_terms_link && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-50 text-green-700 border border-green-100">
            Terms link
          </span>
        )}
        {page.has_consent_checkbox && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-50 text-blue-700 border border-blue-100">
            Consent checkbox
          </span>
        )}
        {page.has_marketing_consent && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-purple-50 text-purple-700 border border-purple-100">
            Marketing consent
          </span>
        )}
        {page.has_bundled_consent_text && (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-amber-50 text-amber-700 border border-amber-200 font-medium">
            Bundled / implied consent
          </span>
        )}
      </div>
      {allSignals.length > 0 && (
        <ul className="mt-1 space-y-0.5">
          {allSignals.slice(0, 5).map((sig, i) => (
            <li key={i} className="text-xs text-gray-500 pl-3 border-l-2 border-gray-200">
              {sig}
            </li>
          ))}
          {allSignals.length > 5 && (
            <li className="text-xs text-gray-400 pl-3">
              +{allSignals.length - 5} more signal(s)
            </li>
          )}
        </ul>
      )}
    </div>
  )
}

export default function ConsentSignalsPanel({ pages }: Props) {
  const pagesWithSignals = pages.filter(
    p =>
      p.has_privacy_link ||
      p.has_terms_link ||
      p.has_consent_checkbox ||
      p.has_marketing_consent ||
      p.has_bundled_consent_text ||
      p.consent_signals.length > 0 ||
      p.dynamic_consent_signals.length > 0
  )

  if (pagesWithSignals.length === 0) return null

  const bundledPages = pages.filter(p => p.has_bundled_consent_text)
  const hasBundledWarning = bundledPages.length > 0

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">Consent Signals</h2>
        <span className="text-xs text-gray-400 italic">heuristic — not a legal assessment</span>
      </div>

      {hasBundledWarning && (
        <div className="bg-amber-50 border border-amber-200 rounded p-3">
          <p className="text-sm font-medium text-amber-800 mb-1">
            Bundled / Implied Consent Detected
          </p>
          <p className="text-xs text-amber-700">
            {bundledPages.length} page{bundledPages.length > 1 ? 's' : ''} appear{bundledPages.length === 1 ? 's' : ''} to
            rely on bundled consent (e.g. "by clicking you agree…") rather than an explicit
            consent checkbox. Manual review is recommended.
          </p>
        </div>
      )}

      <div className="divide-y divide-gray-100 rounded border border-gray-100 overflow-hidden">
        {pagesWithSignals.map((page, i) => (
          <PageConsentRow key={i} page={page} index={i} />
        ))}
      </div>
    </div>
  )
}
