import type { PolicyAnalysis } from '../lib/types'

interface Props {
  analysis: PolicyAnalysis
}

interface SectionRowProps {
  label: string
  present: boolean
}

const DOC_TYPE_LABELS: Record<string, string> = {
  html: 'HTML page',
  pdf: 'PDF document',
  docx: 'DOCX document',
  doc: 'DOC (legacy)',
  unknown: 'Unknown',
}

const PARSE_STATUS_STYLES: Record<string, string> = {
  parsed: 'bg-green-50 text-green-700',
  unreadable: 'bg-yellow-50 text-yellow-700',
  unsupported: 'bg-orange-50 text-orange-700',
  failed: 'bg-red-50 text-red-700',
}

function DocTypeBadge({ docType }: { docType: string }) {
  return (
    <span className="inline-block bg-gray-100 text-gray-600 text-xs font-medium px-2 py-0.5 rounded mr-1">
      {DOC_TYPE_LABELS[docType] ?? docType}
    </span>
  )
}

function ParseStatusBadge({ status }: { status: string }) {
  const style = PARSE_STATUS_STYLES[status] ?? 'bg-gray-100 text-gray-600'
  const label = status === 'parsed' ? 'parsed ✓' : status
  return (
    <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded ${style}`}>
      {label}
    </span>
  )
}

function SectionRow({ label, present }: SectionRowProps) {
  return (
    <tr>
      <td className="px-3 py-2 text-sm text-gray-700">{label}</td>
      <td className="px-3 py-2 text-sm text-center">
        {present ? (
          <span className="text-green-600 font-medium">yes</span>
        ) : (
          <span className="text-gray-300">—</span>
        )}
      </td>
    </tr>
  )
}

export default function PolicyAnalysisPanel({ analysis }: Props) {
  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">
          Policy / Privacy Page Analysis
        </h2>
        <span className="text-xs text-gray-400 italic">heuristic — not a legal assessment</span>
      </div>

      <div className="space-y-1">
        <p className="text-sm text-gray-600 break-all">
          <span className="font-medium text-gray-500">URL: </span>
          <a
            href={analysis.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            {analysis.url}
          </a>
        </p>
        {/* Document type and parse status */}
        <p className="text-sm text-gray-600">
          <span className="font-medium text-gray-500">Source: </span>
          <DocTypeBadge docType={analysis.policy_document_type ?? 'html'} />
          <ParseStatusBadge status={analysis.policy_parse_status ?? 'parsed'} />
        </p>
        {analysis.operator_name && (
          <p className="text-sm text-gray-600">
            <span className="font-medium text-gray-500">Operator (inferred): </span>
            {analysis.operator_name}
          </p>
        )}
        {analysis.operator_contacts.length > 0 && (
          <p className="text-sm text-gray-600">
            <span className="font-medium text-gray-500">Contacts found: </span>
            {analysis.operator_contacts.join(', ')}
          </p>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm border border-gray-100 rounded">
          <thead>
            <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-3 py-2 font-medium">Policy Section</th>
              <th className="px-3 py-2 font-medium text-center">Present</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <SectionRow label="Purpose / goals" present={analysis.has_purpose_section} />
            <SectionRow label="Personal data categories" present={analysis.has_categories_section} />
            <SectionRow label="Legal basis" present={analysis.has_legal_basis_section} />
            <SectionRow label="Third-party processors" present={analysis.has_processor_or_third_party_section} />
            <SectionRow label="Cross-border transfers" present={analysis.has_cross_border_section} />
            <SectionRow label="Data subject rights" present={analysis.has_subject_rights_section} />
            <SectionRow label="Retention / destruction" present={analysis.has_retention_or_destruction_section} />
            <SectionRow label="Localization (152-FZ)" present={analysis.has_localization_statement} />
          </tbody>
        </table>
      </div>

      {analysis.policy_signals.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Signals Detected
          </p>
          <ul className="space-y-1">
            {analysis.policy_signals.map((sig, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                <span className="text-green-500 mt-0.5 shrink-0">&#10003;</span>
                <span>{sig}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
