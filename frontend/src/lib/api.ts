import type { ScanResult, HistoryResponse, ScanDiffRequest, ScanDiffResult } from './types'

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export async function postScan(url: string, notes?: string): Promise<ScanResult> {
  const res = await fetch('/api/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, notes }),
  })
  return handleResponse<ScanResult>(res)
}

export async function getScan(scanId: string): Promise<ScanResult> {
  const res = await fetch(`/api/scan/${encodeURIComponent(scanId)}`)
  return handleResponse<ScanResult>(res)
}

export async function getHistory(limit = 20, offset = 0): Promise<HistoryResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })
  const res = await fetch(`/api/history?${params}`)
  return handleResponse<HistoryResponse>(res)
}

export async function postScanDiff(req: ScanDiffRequest): Promise<ScanDiffResult> {
  const res = await fetch('/api/scan/diff', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  return handleResponse<ScanDiffResult>(res)
}

export async function deleteHistoryItem(scanId: string): Promise<void> {
  const res = await fetch(`/api/history/${encodeURIComponent(scanId)}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = String(body.detail)
    } catch {
      // ignore parse errors
    }
    throw new Error(detail)
  }
}
