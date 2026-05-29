import type { ScanDiffResult, ChangedItem } from '../lib/types'

interface Props {
  diff: ScanDiffResult
}

function SetDiffSection({
  title,
  added,
  removed,
  addedLabel = 'Added',
  removedLabel = 'Removed',
}: {
  title: string
  added: string[]
  removed: string[]
  addedLabel?: string
  removedLabel?: string
}) {
  if (added.length === 0 && removed.length === 0) return null
  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-700 mb-1">{title}</h4>
      <div className="space-y-1">
        {added.map(v => (
          <span
            key={v}
            className="inline-flex items-center mr-2 mb-1 rounded px-2 py-0.5 text-xs bg-green-100 text-green-800"
            title={addedLabel}
          >
            + {v}
          </span>
        ))}
        {removed.map(v => (
          <span
            key={v}
            className="inline-flex items-center mr-2 mb-1 rounded px-2 py-0.5 text-xs bg-red-100 text-red-800"
            title={removedLabel}
          >
            − {v}
          </span>
        ))}
      </div>
    </div>
  )
}

function ChangedItemRow({ item }: { item: ChangedItem }) {
  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-1.5 pr-4 text-sm text-gray-600">{item.label}</td>
      <td className="py-1.5 pr-4 text-sm font-mono text-gray-500">{item.base_value ?? '—'}</td>
      <td className="py-1.5 pr-4 text-sm">→</td>
      <td className="py-1.5 text-sm font-mono text-gray-800">{item.compare_value ?? '—'}</td>
    </tr>
  )
}

export default function ScanDiffPanel({ diff }: Props) {
  const hasSetChanges =
    diff.added_categories.length > 0 ||
    diff.removed_categories.length > 0 ||
    diff.added_vendors.length > 0 ||
    diff.removed_vendors.length > 0 ||
    diff.added_processors.length > 0 ||
    diff.removed_processors.length > 0 ||
    diff.added_gaps.length > 0 ||
    diff.removed_gaps.length > 0

  const hasScalarChanges = diff.changed_items.length > 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg border border-gray-200 p-4">
        <h3 className="text-base font-semibold text-gray-800 mb-3">Scan Comparison</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Base scan</p>
            <p className="font-mono text-gray-700 truncate" title={diff.base_url}>{diff.base_url}</p>
            {diff.base_scanned_at && (
              <p className="text-xs text-gray-400 mt-0.5">{diff.base_scanned_at}</p>
            )}
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide mb-0.5">Compare scan</p>
            <p className="font-mono text-gray-700 truncate" title={diff.compare_url}>{diff.compare_url}</p>
            {diff.compare_scanned_at && (
              <p className="text-xs text-gray-400 mt-0.5">{diff.compare_scanned_at}</p>
            )}
          </div>
        </div>
      </div>

      {/* Summary */}
      {diff.summary_lines.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-blue-800 mb-2">Summary</h4>
          <ul className="space-y-1">
            {diff.summary_lines.map((line, i) => (
              <li key={i} className="text-sm text-blue-700">{line}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Set-level differences */}
      {hasSetChanges && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-4">
          <h3 className="text-sm font-semibold text-gray-800">Set-Level Changes</h3>
          <SetDiffSection
            title="Personal Data Categories"
            added={diff.added_categories}
            removed={diff.removed_categories}
          />
          <SetDiffSection
            title="Third-Party Vendors"
            added={diff.added_vendors}
            removed={diff.removed_vendors}
          />
          <SetDiffSection
            title="Downstream Processors"
            added={diff.added_processors}
            removed={diff.removed_processors}
          />
          <SetDiffSection
            title="Potential Compliance Gaps"
            added={diff.added_gaps}
            removed={diff.removed_gaps}
            addedLabel="New gap"
            removedLabel="Gap resolved"
          />
        </div>
      )}

      {/* Scalar changes */}
      {hasScalarChanges && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-800 mb-3">Field-Level Changes</h3>
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="pb-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide pr-4">Field</th>
                <th className="pb-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide pr-4">Before</th>
                <th className="pb-1.5 pr-4" />
                <th className="pb-1.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">After</th>
              </tr>
            </thead>
            <tbody>
              {diff.changed_items.map((item, i) => (
                <ChangedItemRow key={i} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!hasSetChanges && !hasScalarChanges && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 text-sm text-gray-500 text-center">
          No significant differences detected between the two scans.
        </div>
      )}
    </div>
  )
}
