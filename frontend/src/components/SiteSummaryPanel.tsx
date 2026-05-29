import type { ScanResult } from '../lib/types'

interface Props {
  result: ScanResult
}

interface StatProps {
  label: string
  value: string | number
  sub?: string
}

function Stat({ label, value, sub }: StatProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 text-center">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function SiteSummaryPanel({ result }: Props) {
  const s = result.site_summary
  if (!s) return null

  const hasConsent =
    s.pages_with_privacy_link > 0 ||
    s.pages_with_consent_checkbox > 0 ||
    s.pages_with_marketing_consent > 0

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <h2 className="text-base font-semibold text-gray-900">Site Crawl Summary</h2>

      {/* Coverage stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Pages scanned" value={s.pages_scanned} />
        <Stat label="Pages with forms" value={s.pages_with_forms} />
        <Stat label="Total forms" value={s.total_forms_found} />
        <Stat
          label="Data categories"
          value={s.unique_categories_found.length}
          sub={
            s.unique_categories_found.length > 0
              ? s.unique_categories_found.join(', ')
              : undefined
          }
        />
      </div>

      {/* Third-party hosts */}
      {s.top_third_party_hosts.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
            Top Third-Party Hosts
          </p>
          <div className="flex flex-wrap gap-2">
            {s.top_third_party_hosts.map(host => (
              <span
                key={host}
                className="inline-block bg-amber-50 border border-amber-200 text-amber-700 text-xs font-mono px-2 py-0.5 rounded"
              >
                {host}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Consent / privacy signal summary */}
      <div>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
          Consent &amp; Privacy Signals
          <span className="ml-1 normal-case font-normal text-gray-400">
            (heuristic — not a legal assessment)
          </span>
        </p>
        {hasConsent ? (
          <div className="grid grid-cols-1 gap-1 sm:grid-cols-3">
            <ConsentStat
              label="Pages with privacy link"
              count={s.pages_with_privacy_link}
              total={s.pages_scanned}
            />
            <ConsentStat
              label="Pages with consent checkbox"
              count={s.pages_with_consent_checkbox}
              total={s.pages_scanned}
            />
            <ConsentStat
              label="Pages with marketing consent"
              count={s.pages_with_marketing_consent}
              total={s.pages_scanned}
            />
          </div>
        ) : (
          <p className="text-sm text-gray-400">No consent/privacy signals detected across scanned pages.</p>
        )}
      </div>
    </div>
  )
}

interface ConsentStatProps {
  label: string
  count: number
  total: number
}

function ConsentStat({ label, count, total }: ConsentStatProps) {
  const present = count > 0
  return (
    <div className={`flex items-center gap-2 rounded px-3 py-2 text-sm ${present ? 'bg-green-50' : 'bg-gray-50'}`}>
      <span className={`text-base ${present ? 'text-green-500' : 'text-gray-300'}`}>
        {present ? '✓' : '–'}
      </span>
      <span className={present ? 'text-gray-700' : 'text-gray-400'}>
        {label}
        {present && (
          <span className="ml-1 text-xs text-gray-400">
            ({count}/{total} pages)
          </span>
        )}
      </span>
    </div>
  )
}
