import { ChangeEvent, DragEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../services/api'
import {
  deleteDocument,
  downloadDocument,
  getDocument,
  getDocumentContent,
  listDocuments,
  processDocument,
  uploadDocument,
} from '../services/documents'
import type { DocumentContentResponse, DocumentDetails, DocumentRecord } from '../types/documents'

const maxUploadSizeMb = Number(import.meta.env.VITE_MAX_UPLOAD_SIZE_MB ?? 25)
const supportedExtensions = ['.pdf', '.docx']

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value))
}

function statusLabel(status: DocumentRecord['status']): string {
  if (status === 'processing') return 'Processing...'
  if (status === 'processed') return 'Processed'
  if (status === 'failed') return 'Processing Failed'
  return 'Uploaded'
}

export default function KnowledgeBasePage() {
  const { token, logout } = useAuth()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [total, setTotal] = useState(0)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [processingId, setProcessingId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [details, setDetails] = useState<DocumentDetails | null>(null)
  const [content, setContent] = useState<DocumentContentResponse | null>(null)
  const [contentLoading, setContentLoading] = useState(false)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    listDocuments(token)
      .then((response) => {
        if (cancelled) return
        setDocuments(response.items)
        setTotal(response.total)
      })
      .catch((requestError) => {
        if (cancelled) return
        if (requestError instanceof ApiError && requestError.status === 401) {
          logout()
          navigate('/login', { replace: true })
        } else setError('Unable to load documents.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [token, logout, navigate])

  const loadDocuments = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await listDocuments(token)
      setDocuments(response.items)
      setTotal(response.total)
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout()
        navigate('/login', { replace: true })
      } else setError('Unable to load documents.')
    } finally {
      setIsLoading(false)
    }
  }

  const selectFile = (selected: File | undefined) => {
    setError('')
    setSuccess('')
    if (!selected) return
    const extension = `.${selected.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!supportedExtensions.includes(extension)) {
      setFile(null)
      setError('Only PDF and DOCX files are supported.')
      return
    }
    if (selected.size === 0) {
      setFile(null)
      setError('The selected file is empty.')
      return
    }
    if (selected.size > maxUploadSizeMb * 1024 * 1024) {
      setFile(null)
      setError(`Files must be ${maxUploadSizeMb} MB or smaller.`)
      return
    }
    setFile(selected)
  }

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0])
  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault()
    selectFile(event.dataTransfer.files[0])
  }

  const handleUpload = async () => {
    if (!file || !token) {
      setError('Choose a PDF or DOCX file first.')
      return
    }
    setIsUploading(true)
    setError('')
    setSuccess('')
    try {
      await uploadDocument(token, file, title)
      setFile(null)
      setTitle('')
      if (inputRef.current) inputRef.current.value = ''
      setSuccess('Document uploaded successfully. Processing has not started.')
      await loadDocuments()
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout()
        navigate('/login', { replace: true })
      } else if (requestError instanceof ApiError) setError(requestError.message)
      else setError('Unable to upload document.')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDetails = async (id: string) => {
    if (!token) return
    try {
      setDetails(await getDocument(token, id))
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout()
        navigate('/login', { replace: true })
      } else setError('Unable to load document details.')
    }
  }

  const handleProcess = async (id: string) => {
    if (!token) return
    setProcessingId(id)
    setError('')
    setSuccess('')
    try {
      const result = await processDocument(token, id)
      if (result.status === 'processed') setSuccess('Document processed successfully.')
      else setError(result.processing_error ?? 'Document processing failed.')
      await loadDocuments()
      if (details?.id === id) await handleDetails(id)
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout()
        navigate('/login', { replace: true })
      } else if (requestError instanceof ApiError) setError(requestError.message)
      else setError('Unable to process document.')
    } finally {
      setProcessingId(null)
    }
  }

  const handleContent = async (id: string) => {
    if (!token) return
    setContentLoading(true)
    try {
      setContent(await getDocumentContent(token, id))
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout()
        navigate('/login', { replace: true })
      } else setError('Unable to load extracted content.')
    } finally {
      setContentLoading(false)
    }
  }

  const handleDownload = async (document: DocumentRecord) => {
    if (!token) return
    try {
      const blob = await downloadDocument(token, document.id)
      const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a')
      anchor.href = url
      anchor.download = document.file_name
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout()
        navigate('/login', { replace: true })
      } else setError('Unable to download document.')
    }
  }

  const handleDelete = async (document: DocumentRecord) => {
    if (!token || !window.confirm(`Delete “${document.file_name}”?\n\nThis will remove the document from the knowledge base.`)) return
    try {
      await deleteDocument(token, document.id)
      setSuccess('Document deleted successfully.')
      await loadDocuments()
    } catch (requestError) {
      if (requestError instanceof ApiError && requestError.status === 401) {
        logout()
        navigate('/login', { replace: true })
      } else setError('Unable to delete document.')
    }
  }

  const selectedLabel = useMemo(
    () => (file ? `${file.name} · ${formatBytes(file.size)}` : 'Choose a PDF or DOCX file'),
    [file],
  )

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-6xl">
        <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">Knowledge workspace</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight">Knowledge Base</h1>
            <p className="mt-2 text-slate-400">Upload documents, then explicitly process them for text inspection.</p>
          </div>
          <button className="self-start rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400 sm:self-auto" onClick={() => navigate('/dashboard')}>
            Back to dashboard
          </button>
        </header>

        <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end">
            <div className="flex-1">
              <label className="block text-sm font-medium text-slate-200">
                Document title <span className="font-normal text-slate-500">(optional)</span>
                <input className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-400" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Derived from filename when empty" />
              </label>
            </div>
            <div className="flex-1">
              <label className="block cursor-pointer rounded-lg border border-dashed border-slate-600 bg-slate-950 px-4 py-3 text-sm text-slate-300 hover:border-cyan-400" onDragOver={(event) => event.preventDefault()} onDrop={onDrop}>
                <span className="block truncate">{selectedLabel}</span>
                <span className="mt-1 block text-xs text-slate-500">PDF/DOCX · up to {maxUploadSizeMb} MB · drag and drop supported</span>
                <input ref={inputRef} className="sr-only" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={onFileChange} />
              </label>
            </div>
            <button className="rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50" disabled={!file || isUploading} onClick={() => void handleUpload()}>
              {isUploading ? 'Uploading...' : 'Upload document'}
            </button>
          </div>
          {error && <p className="mt-4 rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-300">{error}</p>}
          {success && <p className="mt-4 rounded-lg border border-emerald-900/60 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">{success}</p>}
        </section>

        <section className="mt-8 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900">
          <div className="flex items-center justify-between border-b border-slate-800 px-6 py-5">
            <div><h2 className="font-semibold">Documents</h2><p className="mt-1 text-sm text-slate-500">{total} document{total === 1 ? '' : 's'}</p></div>
          </div>
          {isLoading ? <p className="px-6 py-12 text-center text-slate-400">Loading documents...</p> : documents.length === 0 ? <p className="px-6 py-12 text-center text-slate-400">No knowledge documents uploaded yet.</p> : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[800px] text-left text-sm">
                <thead className="bg-slate-950/50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-6 py-4">Document</th><th className="px-6 py-4">Type</th><th className="px-6 py-4">Size</th><th className="px-6 py-4">Status</th><th className="px-6 py-4">Uploaded</th><th className="px-6 py-4">Actions</th></tr></thead>
                <tbody className="divide-y divide-slate-800">{documents.map((document) => <tr key={document.id} className="text-slate-300"><td className="px-6 py-4"><p className="font-medium text-slate-100">{document.title}</p><p className="mt-1 text-xs text-slate-500">{document.file_name}</p></td><td className="px-6 py-4 uppercase">{document.file_type}</td><td className="px-6 py-4">{formatBytes(document.file_size)}</td><td className="px-6 py-4"><span className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs text-cyan-300">{statusLabel(document.status)}</span></td><td className="px-6 py-4">{formatDate(document.created_at)}</td><td className="px-6 py-4"><div className="flex flex-wrap gap-3"><button className="text-cyan-300 hover:text-cyan-200" onClick={() => void handleDetails(document.id)}>Details</button>{document.status === 'processed' && <button className="text-cyan-300 hover:text-cyan-200" onClick={() => void handleContent(document.id)}>Content</button>}{document.status === 'uploaded' || document.status === 'failed' ? <button className="text-amber-300 hover:text-amber-200" disabled={processingId === document.id} onClick={() => void handleProcess(document.id)}>{processingId === document.id ? 'Processing...' : document.status === 'failed' ? 'Retry' : 'Process'}</button> : document.status === 'processing' ? <span className="text-amber-300">Processing...</span> : null}<button className="text-slate-300 hover:text-white" onClick={() => void handleDownload(document)}>Download</button><button className="text-red-300 hover:text-red-200" onClick={() => void handleDelete(document)}>Delete</button></div></td></tr>)}</tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      {details && <div className="fixed inset-0 z-10 flex items-center justify-center bg-slate-950/80 px-6" role="dialog" aria-modal="true"><div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"><div className="flex items-start justify-between gap-4"><div><p className="text-sm text-cyan-400">Document details</p><h2 className="mt-2 text-2xl font-semibold">{details.title}</h2></div><button className="text-2xl text-slate-400 hover:text-white" onClick={() => setDetails(null)} aria-label="Close details">×</button></div><dl className="mt-6 grid grid-cols-2 gap-5 text-sm"><div><dt className="text-slate-500">Filename</dt><dd className="mt-1 break-words text-slate-200">{details.file_name}</dd></div><div><dt className="text-slate-500">Type</dt><dd className="mt-1 uppercase text-slate-200">{details.file_type}</dd></div><div><dt className="text-slate-500">Size</dt><dd className="mt-1 text-slate-200">{formatBytes(details.file_size)}</dd></div><div><dt className="text-slate-500">Status</dt><dd className="mt-1 text-slate-200">{statusLabel(details.status)}</dd></div><div><dt className="text-slate-500">Pages</dt><dd className="mt-1 text-slate-200">{details.page_count ?? 'Not available for this format'}</dd></div><div><dt className="text-slate-500">Extracted blocks</dt><dd className="mt-1 text-slate-200">{details.extracted_block_count}</dd></div><div><dt className="text-slate-500">Chunk count</dt><dd className="mt-1 text-slate-200">{details.chunk_count}</dd></div><div><dt className="text-slate-500">Uploaded</dt><dd className="mt-1 text-slate-200">{formatDate(details.created_at)}</dd></div>{details.uploader && <div><dt className="text-slate-500">Uploader</dt><dd className="mt-1 text-slate-200">{details.uploader.name}</dd></div>}</dl>{details.processing_error && <p className="mt-5 rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-300">{details.processing_error}</p>}<div className="mt-6 flex flex-wrap gap-3">{(details.status === 'uploaded' || details.status === 'failed') && <button className="rounded-lg bg-amber-400 px-4 py-2 font-semibold text-slate-950" onClick={() => void handleProcess(details.id)}>{details.status === 'failed' ? 'Retry processing' : 'Process document'}</button>}{details.status === 'processed' && <button className="rounded-lg border border-cyan-400 px-4 py-2 text-cyan-300" onClick={() => void handleContent(details.id)}>View extracted content</button>}</div></div></div>}

      {content && <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-950/80 px-6" role="dialog" aria-modal="true"><div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"><div className="flex items-center justify-between"><div><p className="text-sm text-cyan-400">Extracted content</p><h2 className="mt-2 text-2xl font-semibold">Source blocks</h2></div><button className="text-2xl text-slate-400 hover:text-white" onClick={() => setContent(null)} aria-label="Close extracted content">×</button></div>{contentLoading ? <p className="py-10 text-center text-slate-400">Loading extracted content...</p> : <div className="mt-6 space-y-4">{content.items.map((item) => <article key={item.sequence_index} className="rounded-lg border border-slate-800 bg-slate-950 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-cyan-400">{item.page_number === null ? `Section ${item.sequence_index + 1}` : `Page ${item.page_number}`}</p><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">{item.content}</p></article>)}</div>}</div></div>}
    </main>
  )
}
