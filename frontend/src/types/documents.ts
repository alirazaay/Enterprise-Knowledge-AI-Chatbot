export type DocumentStatus = 'uploaded' | 'processing' | 'indexed' | 'failed'

export interface DocumentRecord {
  id: string
  title: string
  file_name: string
  file_type: string
  file_size: number
  page_count: number | null
  chunk_count: number
  status: DocumentStatus
  uploaded_by: string
  created_at: string
  updated_at: string
}

export interface DocumentDetails extends DocumentRecord {
  uploader?: { id: string; name: string; email: string; role: string } | null
}

export interface DocumentListResponse {
  items: DocumentRecord[]
  page: number
  page_size: number
  total: number
  total_pages: number
}
