import { useState } from 'react'
import type { VisitedPageItem } from '../lib/types'

interface Props {
  pages: VisitedPageItem[]
}

interface PageRowProps {
  page: VisitedPageItem
}

function PageRow({ page }: PageRowProps) {
  const [expanded, setExpanded] = useState(false)
  const hasDetails =
    page.interactions_performed.length > 0 || page.dynamic_consent_signals.length > 0

  return (
    <div className="border border-gray-100 rounded">
      <button
        className="w-full flex items-center justify-between px-3 py-2 text-sm text-left hover:bg-gray-50"
        onClick={() => hasDetails && setExpanded(v => !v)}
        disabled={!hasDetails}
      >
        <span className="break-all text-gray-700 font-mono text-xs">{page.url}</span>
        <div className="flex items-center gap-3 ml-3 shrink-0 text-xs text-gray-500">
          <span title="Interactions">{page.interactions_performed.length} interactions</span>
          <span title="Hidden forms revealed">{page.hidden_forms_revealed} hidden forms</span>
          <span title="Modal forms found">{page.modal_forms_found} modals</span>
          {hasDetails && (
            <span className="text-gray-400">{expanded ? '▲' : '▼'}</span>
          )}
        </div>
      </button>

      {expanded && hasDetails && (
        <div className="px-3 pb-3 space-y-2 border-t border-gray-100 bg-gray-50">
          {page.interactions_performed.length > 0 && (
            <div className="pt-2">
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Interactions performed
              </p>
              <ul className="space-y-0.5">
                {page.interactions_performed.map((act, i) => (
                  <li key={i} className="text-xs text-gray-600 font-mono">
                    {act}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {page.dynamic_consent_signals.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
                Dynamic consent signals revealed
              </p>
              <ul className="space-y-0.5">
                {page.dynamic_consent_signals.map((sig, i) => (
                  <li key={i} className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-0.5">
                    {sig}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function InteractiveFindingsPanel({ pages }: Props) {
  const interactivePages = pages.filter(
    p => p.interactions_performed.length > 0 || p.hidden_forms_revealed > 0
  )

  if (interactivePages.length === 0) return null

  const totalInteractions = interactivePages.reduce(
    (sum, p) => sum + p.interactions_performed.length, 0
  )
  const totalHidden = interactivePages.reduce((sum, p) => sum + p.hidden_forms_revealed, 0)
  const totalModal = interactivePages.reduce((sum, p) => sum + p.modal_forms_found, 0)

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">
          Interactive Discovery Findings
        </h2>
        <span className="text-xs text-gray-400 italic">no forms submitted</span>
      </div>

      <p className="text-xs text-gray-500">
        CTA-like buttons were clicked to reveal hidden, modal, or accordion content.
        No forms were submitted and no personal data was entered.
      </p>

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-700">{totalInteractions}</p>
          <p className="text-xs text-gray-500 mt-0.5">Total interactions</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-700">{totalHidden}</p>
          <p className="text-xs text-gray-500 mt-0.5">Hidden forms revealed</p>
        </div>
        <div className="bg-blue-50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-blue-700">{totalModal}</p>
          <p className="text-xs text-gray-500 mt-0.5">Modal forms found</p>
        </div>
      </div>

      <div className="space-y-1">
        {interactivePages.map((page, i) => (
          <PageRow key={i} page={page} />
        ))}
      </div>
    </div>
  )
}
