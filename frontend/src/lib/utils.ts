export function formatDate(iso: string): string {
  const d = new Date(iso)
  const day = d.getDate().toString().padStart(2, '0')
  const month = d.toLocaleString('en-GB', { month: 'short' })
  const year = d.getFullYear()
  const hh = d.getHours().toString().padStart(2, '0')
  const mm = d.getMinutes().toString().padStart(2, '0')
  return `${day} ${month} ${year} ${hh}:${mm}`
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 0.9) return 'High'
  if (confidence >= 0.6) return 'Medium'
  return 'Low'
}

export function confidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'text-green-600'
  if (confidence >= 0.6) return 'text-yellow-500'
  return 'text-red-500'
}

export function statusColor(status: string): string {
  switch (status) {
    case 'pending':
      return 'bg-gray-100 text-gray-600'
    case 'processing':
      return 'bg-blue-100 text-blue-700'
    case 'complete':
      return 'bg-green-100 text-green-700'
    case 'failed':
      return 'bg-red-100 text-red-700'
    default:
      return 'bg-gray-100 text-gray-600'
  }
}

export function relevanceLabel(relevance: string | null): string {
  switch (relevance) {
    case 'registration':
      return 'Registration'
    case 'likely_registration':
      return 'Likely Registration'
    case 'login':
      return 'Login'
    case 'newsletter':
      return 'Newsletter'
    case 'contact':
      return 'Contact'
    case 'checkout':
      return 'Checkout'
    case 'callback':
      return 'Callback / Demo'
    case 'ambiguous':
      return 'Ambiguous'
    case null:
      return 'Unknown'
    default:
      return relevance
  }
}

export function relevanceColor(relevance: string | null): string {
  switch (relevance) {
    case 'registration':
    case 'likely_registration':
      return 'bg-purple-100 text-purple-700'
    case 'login':
      return 'bg-blue-100 text-blue-700'
    case 'newsletter':
      return 'bg-green-100 text-green-700'
    case 'contact':
    case 'callback':
      return 'bg-yellow-100 text-yellow-700'
    case 'checkout':
      return 'bg-orange-100 text-orange-700'
    default:
      return 'bg-gray-100 text-gray-500'
  }
}

export const HIGH_RISK_CATEGORIES = new Set([
  'national_id',
  'financial',
  'health',
  'date_of_birth',
  'password',
])
