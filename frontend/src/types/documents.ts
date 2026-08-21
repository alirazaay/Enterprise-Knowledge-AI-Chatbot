export type DocumentStatus = 'uploaded' | 'processing' | 'processed' | 'indexed' | 'failed'

export interface DocumentRecord {
  id: string
  title: string
  file_name: string
  file_type: string
  file_size: number
  page_count: number | null
  chunk_count: number
  status: DocumentStatus
  processing_error: string | null
  uploaded_by: string
  created_at: string
  updated_at: string
}

export interface DocumentDetails extends DocumentRecord {
  extracted_block_count: number
  uploader?: { id: string; name: string; email: string; role: string } | null
}

export interface DocumentContentItem {
  page_number: number | null
  sequence_index: number
  content: string
}

export interface DocumentContentResponse {
  document_id: string
  items: DocumentContentItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface DocumentListResponse {
  items: DocumentRecord[]
  page: number
  page_size: number
  total: number
  total_pages: number
}
