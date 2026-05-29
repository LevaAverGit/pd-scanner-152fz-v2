import type { FZ152Assessment, OperatorMetadata } from '../lib/types'

interface Props {
  assessment: FZ152Assessment
  operatorMetadata?: OperatorMetadata | null
}

function RiskBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: 'bg-green-100 text-green-800 border-green-200',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    high: 'bg-red-100 text-red-800 border-red-200',
  }
  const cls = colors[level] ?? 'bg-gray-100 text-gray-800 border-gray-200'
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${cls} uppercase`}>
      {level}
    </span>
  )
}

const POLICY_SECTIONS: Array<[string, keyof FZ152Assessment]> = [
  ['Purpose / processing goals', 'policy_has_purpose_section'],
  ['Personal data categories', 'policy_has_categories_section'],
  ['Legal basis', 'policy_has_legal_basis_section'],
  ['Third-party / processor disclosure', 'policy_has_processor_or_third_party_section'],
  ['Cross-border transfers', 'policy_has_cross_border_section'],
  ['Data subject rights', 'policy_has_subject_rights_section'],
  ['Retention / destruction', 'policy_has_retention_or_destruction_section'],
  ['Localization (Art. 18.1)', 'policy_has_localization_statement'],
]

export default function FZ152AssessmentPanel({ assessment: fz, operatorMetadata: om }: Props) {
  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">152-FZ Public Evidence Summary</h2>
        <RiskBadge level={fz.overall_public_risk_level} />
      </div>

      <p className="text-xs text-gray-500 italic border-l-2 border-gray-200 pl-2">
        {fz.disclaimer}
      </p>

      {/* Operator & Policy Presence */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Operator &amp; Policy Public Presence</h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          {fz.operator_name && (
            <>
              <dt className="text-gray-500">Operator (inferred)</dt>
              <dd className="text-gray-900 font-medium">{fz.operator_name}</dd>
            </>
          )}
          {fz.operator_contacts.length > 0 && (
            <>
              <dt className="text-gray-500">Contacts found</dt>
              <dd className="text-gray-900">{fz.operator_contacts.slice(0, 3).join(', ')}</dd>
            </>
          )}
          <dt className="text-gray-500">Policy publicly available</dt>
          <dd className={fz.policy_publicly_available ? 'text-green-700 font-medium' : 'text-red-600'}>
            {fz.policy_publicly_available ? 'Yes' : 'Not detected'}
          </dd>
          <dt className="text-gray-500">Privacy links found</dt>
          <dd className="text-gray-900">{fz.privacy_links_found}</dd>
        </dl>
      </div>

      {/* Data Collection Scope */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Data Collection Scope</h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <dt className="text-gray-500">Forms collecting PD</dt>
          <dd className="text-gray-900">{fz.forms_collecting_pd}</dd>
          <dt className="text-gray-500">Consent mechanism</dt>
          <dd className="text-gray-900 font-medium">{fz.consent_mechanism_type}</dd>
          {fz.detected_pd_categories.length > 0 && (
            <>
              <dt className="text-gray-500">PD categories detected</dt>
              <dd className="text-gray-900">{fz.detected_pd_categories.join(', ')}</dd>
            </>
          )}
        </dl>
      </div>

      {/* Policy Section Coverage */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Policy Section Coverage</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-3 py-2 font-medium">Section</th>
                <th className="px-3 py-2 font-medium">Publicly Evidenced</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {POLICY_SECTIONS.map(([label, key]) => {
                const val = fz[key] as boolean
                return (
                  <tr key={key}>
                    <td className="px-3 py-1.5 text-gray-700">{label}</td>
                    <td className="px-3 py-1.5">
                      {val ? (
                        <span className="text-green-600 font-medium">✓</span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Processing & Routing Scope */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-2">Processing &amp; Routing Scope</h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
          <dt className="text-gray-500">Third-party routing signals</dt>
          <dd className={fz.third_party_routing_present ? 'text-amber-700 font-medium' : 'text-gray-400'}>
            {fz.third_party_routing_present ? 'Yes' : 'Not detected'}
          </dd>
          <dt className="text-gray-500">Observed form submission</dt>
          <dd className="text-gray-900">{fz.observed_submit_present ? 'Yes' : 'No / not enabled'}</dd>
          <dt className="text-gray-500">Processor map entries</dt>
          <dd className="text-gray-900">{fz.processor_map_present ? 'Yes' : 'No'}</dd>
          <dt className="text-gray-500">Metrics/tracking signals</dt>
          <dd className={fz.metrics_or_tracking_present ? 'text-amber-700' : 'text-gray-400'}>
            {fz.metrics_or_tracking_present ? 'Yes' : 'Not detected'}
          </dd>
          <dt className="text-gray-500">Operator-supplied evidence</dt>
          <dd className="text-gray-900">{fz.operator_supplied_evidence_present ? 'Yes' : 'None'}</dd>
        </dl>
      </div>

      {/* Potential Gaps */}
      {fz.potential_gaps.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-1">Potential Public-Signal Gaps</h3>
          <p className="text-xs text-gray-500 italic mb-2">
            Potential gaps from public signals only — not confirmed violations.
          </p>
          <ul className="space-y-1">
            {fz.potential_gaps.map((gap, i) => (
              <li key={i} className="flex gap-2 text-sm text-gray-700">
                <span className="text-amber-500 mt-0.5 flex-shrink-0">!</span>
                <span>{gap}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Manual Validation Checklist */}
      {fz.manual_validation_targets.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-2">Manual Validation Checklist</h3>
          <ul className="space-y-1">
            {fz.manual_validation_targets.map((target, i) => (
              <li key={i} className="flex gap-2 text-sm text-gray-700">
                <input type="checkbox" className="mt-0.5 flex-shrink-0" readOnly />
                <span>{target}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Operator-Supplied Metadata */}
      {om && (
        <div className="border-t pt-3">
          <h3 className="text-sm font-medium text-gray-700 mb-1">Operator-Supplied Metadata</h3>
          <p className="text-xs text-amber-700 italic mb-2">
            Note: The following was supplied by the operator and has NOT been verified by the scanner.
          </p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            {om.legal_name && (
              <>
                <dt className="text-gray-500">Legal name</dt>
                <dd className="text-gray-900">{om.legal_name}</dd>
              </>
            )}
            {om.inn && (
              <>
                <dt className="text-gray-500">INN</dt>
                <dd className="text-gray-900 font-mono">{om.inn}</dd>
              </>
            )}
            {om.ogrn && (
              <>
                <dt className="text-gray-500">OGRN</dt>
                <dd className="text-gray-900 font-mono">{om.ogrn}</dd>
              </>
            )}
          </dl>
          {om.notes.length > 0 && (
            <ul className="mt-2 space-y-0.5">
              {om.notes.slice(0, 3).map((note, i) => (
                <li key={i} className="text-xs text-gray-500">- {note}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
