import { ApiError, api } from './api'
import type { DocumentContentResponse, DocumentDetails, DocumentListResponse, DocumentRecord } from '../types/documents'

export function uploadDocument(token: string, file: File, title?: string): Promise<DocumentRecord> {
  const form = new FormData()
  form.append('file', file)
  if (title?.trim()) form.append('title', title.trim())
  return api.requestWithToken<DocumentRecord>('/documents', token, {
    method: 'POST',
    body: form,
    headers: {},
  })
}

export function listDocuments(token: string, page = 1, pageSize = 20): Promise<DocumentListResponse> {
  return api.requestWithToken<DocumentListResponse>(`/documents?page=${page}&page_size=${pageSize}`, token)
}

export function getDocument(token: string, id: string): Promise<DocumentDetails> {
  return api.requestWithToken<DocumentDetails>(`/documents/${id}`, token)
}

export function processDocument(token: string, id: string): Promise<{ document_id: string; status: string; page_count: number | null; extracted_block_count: number; processing_error: string | null }> {
  return api.requestWithToken(`/documents/${id}/process`, token, { method: 'POST' })
}

export function getDocumentContent(token: string, id: string): Promise<DocumentContentResponse> {
  return api.requestWithToken<DocumentContentResponse>(`/documents/${id}/content`, token)
}

export function deleteDocument(token: string, id: string): Promise<void> {
  return api.requestWithToken<void>(`/documents/${id}`, token, { method: 'DELETE' })
}

export async function downloadDocument(token: string, id: string): Promise<Blob> {
  const response = await fetch(`${api.baseUrl}/documents/${id}/file`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!response.ok) throw new ApiError('Unable to download document.', response.status)
  return response.blob()
}
