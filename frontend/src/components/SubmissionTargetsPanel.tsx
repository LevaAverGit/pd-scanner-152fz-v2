import type { VisitedPageItem } from '../lib/types'

interface Props {
  pages: VisitedPageItem[]
}

const TARGET_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  first_party: { label: 'First-party', color: 'text-green-600' },
  third_party: { label: 'Third-party', color: 'text-amber-600 font-medium' },
  relative: { label: 'Relative (same-site)', color: 'text-green-500' },
  unknown: { label: 'Unknown', color: 'text-gray-400' },
}

function TargetTypePill({ type }: { type: string }) {
  const cfg = TARGET_TYPE_LABELS[type] ?? TARGET_TYPE_LABELS.unknown
  return <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
}

export default function SubmissionTargetsPanel({ pages }: Props) {
  const relevantPages = pages.filter(
    p => p.forms_found > 0 && p.submission_evidence.length > 0
  )

  if (relevantPages.length === 0) return null

  const thirdPartyPages = relevantPages.filter(p => p.has_third_party_submission_hint)

  return (
    <div className="bg-white border rounded-lg p-4 space-y-3">
      <div>
        <h2 className="text-base font-semibold text-gray-900">Form Submission Analysis</h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Passive DOM inspection only — no forms were submitted.
        </p>
      </div>

      {thirdPartyPages.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
          <p className="text-xs font-medium text-amber-800">
            {thirdPartyPages.length === 1
              ? '1 page has forms that appear to submit to a third-party endpoint.'
              : `${thirdPartyPages.length} pages have forms that appear to submit to third-party endpoints.`}
          </p>
        </div>
      )}

      <div className="space-y-4">
        {relevantPages.map((page, i) => (
          <div key={i} className="border rounded-md p-3 bg-gray-50 space-y-2">
            <a
              href={page.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-blue-600 hover:text-blue-800 break-all"
            >
              {page.url}
            </a>

            <div className="flex flex-wrap gap-3 text-xs">
              {page.probable_form_platform && (
                <span>
                  <span className="text-gray-500">Form platform:</span>{' '}
                  <span className="font-medium text-purple-700">{page.probable_form_platform}</span>
                </span>
              )}
              {page.probable_crm_or_capture_tool && (
                <span>
                  <span className="text-gray-500">CRM / lead capture:</span>{' '}
                  <span className="font-medium text-violet-700">{page.probable_crm_or_capture_tool}</span>
                </span>
              )}
              {page.submission_target_type !== 'unknown' && (
                <span>
                  <span className="text-gray-500">Target:</span>{' '}
                  <TargetTypePill type={page.submission_target_type} />
                  {page.submission_method && (
                    <span className="ml-1 text-gray-400 uppercase text-xs">
                      {page.submission_method}
                    </span>
                  )}
                </span>
              )}
            </div>

            {page.submission_evidence.length > 0 && (
              <ul className="space-y-0.5 mt-1">
                {page.submission_evidence.map((ev, j) => (
                  <li key={j} className="text-xs text-gray-500 pl-2 border-l border-gray-300">
                    {ev}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
