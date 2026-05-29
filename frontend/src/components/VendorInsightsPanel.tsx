import type { VendorSummaryItem } from '../lib/types'

interface Props {
  vendors: VendorSummaryItem[]
}

const CLASS_LABELS: Record<string, string> = {
  analytics: 'Analytics',
  advertising: 'Advertising',
  tag_manager: 'Tag Manager',
  chat_widget: 'Chat Widget',
  call_tracking: 'Call Tracking',
  form_platform: 'Form Platform',
  crm_or_lead_capture: 'CRM / Lead Capture',
  consent_management: 'Consent Management',
  cdn_or_static: 'CDN / Static Assets',
  fonts: 'Web Fonts',
  maps: 'Maps',
  video_or_media: 'Video / Media',
  payment: 'Payment',
  social: 'Social',
  unknown: 'Unknown',
}

const CLASS_COLORS: Record<string, string> = {
  analytics: 'bg-blue-50 text-blue-700 border-blue-200',
  advertising: 'bg-red-50 text-red-700 border-red-200',
  tag_manager: 'bg-orange-50 text-orange-700 border-orange-200',
  chat_widget: 'bg-teal-50 text-teal-700 border-teal-200',
  call_tracking: 'bg-rose-50 text-rose-700 border-rose-200',
  form_platform: 'bg-purple-50 text-purple-700 border-purple-200',
  crm_or_lead_capture: 'bg-violet-50 text-violet-700 border-violet-200',
  consent_management: 'bg-green-50 text-green-700 border-green-200',
  cdn_or_static: 'bg-gray-50 text-gray-500 border-gray-200',
  fonts: 'bg-gray-50 text-gray-400 border-gray-200',
  maps: 'bg-cyan-50 text-cyan-700 border-cyan-200',
  video_or_media: 'bg-yellow-50 text-yellow-700 border-yellow-200',
  payment: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  social: 'bg-sky-50 text-sky-700 border-sky-200',
  unknown: 'bg-gray-50 text-gray-400 border-gray-200',
}

const HIGH_INTEREST = new Set([
  'form_platform',
  'crm_or_lead_capture',
  'call_tracking',
  'advertising',
  'tag_manager',
])

function VendorClassBadge({ vendorClass }: { vendorClass: string }) {
  const label = CLASS_LABELS[vendorClass] ?? vendorClass
  const color = CLASS_COLORS[vendorClass] ?? 'bg-gray-50 text-gray-500 border-gray-200'
  return (
    <span className={`inline-block text-xs font-medium px-1.5 py-0.5 rounded border ${color}`}>
      {label}
    </span>
  )
}

export default function VendorInsightsPanel({ vendors }: Props) {
  if (vendors.length === 0) return null

  const highInterest = vendors.filter(v => HIGH_INTEREST.has(v.vendor_class))

  return (
    <div className="bg-white border rounded-lg p-4 space-y-4">
      <div>
        <h2 className="text-base font-semibold text-gray-900">
          Vendor / Third-Party Ecosystem
        </h2>
        <p className="text-xs text-gray-400 mt-0.5">
          Classification is based on hostname pattern matching — passive analysis only.
        </p>
      </div>

      {highInterest.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-md p-3">
          <p className="text-xs font-medium text-amber-800 mb-1">
            Vendors requiring data-flow review:
          </p>
          <ul className="space-y-1">
            {highInterest.map(v => (
              <li key={v.host} className="text-xs text-amber-700">
                <span className="font-medium">{v.vendor_name ?? v.host}</span>
                {v.vendor_name && (
                  <span className="ml-1 font-mono text-amber-500">({v.host})</span>
                )}
                {' — '}
                <VendorClassBadge vendorClass={v.vendor_class} />
                {v.notes.length > 0 && (
                  <ul className="mt-0.5 ml-3 list-disc text-amber-600">
                    {v.notes.map((n, i) => <li key={i}>{n}</li>)}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-3 py-2 font-medium">Host</th>
              <th className="px-3 py-2 font-medium">Vendor</th>
              <th className="px-3 py-2 font-medium">Class</th>
              <th className="px-3 py-2 font-medium">First Seen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {vendors.map((v, i) => (
              <tr key={v.host} className={i % 2 === 1 ? 'bg-gray-50' : 'bg-white'}>
                <td className="px-3 py-2 font-mono text-xs text-gray-700 break-all">
                  {v.host}
                </td>
                <td className="px-3 py-2 text-xs text-gray-700">
                  {v.vendor_name ?? <span className="text-gray-400 italic">unknown</span>}
                </td>
                <td className="px-3 py-2">
                  <VendorClassBadge vendorClass={v.vendor_class} />
                </td>
                <td className="px-3 py-2 text-xs text-gray-400 break-all max-w-xs truncate">
                  {v.first_seen_on ?? '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
