import { ChangeEvent, DragEvent, useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../services/api'
import { deleteDocument, downloadDocument, getDocument, getDocumentChunks, getDocumentContent, indexDocument, listDocuments, processDocument, uploadDocument } from '../services/documents'
import type { DocumentChunkResponse, DocumentContentResponse, DocumentDetails, DocumentRecord } from '../types/documents'

const maxUploadSizeMb = Number(import.meta.env.VITE_MAX_UPLOAD_SIZE_MB ?? 25)
const supportedExtensions = ['.pdf', '.docx']

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1 }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`
}

function formatDate(value: string): string { return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value)) }

function statusLabel(status: DocumentRecord['status']): string {
  if (status === 'processing') return 'Processing...'
  if (status === 'processed') return 'Processed'
  if (status === 'indexing') return 'Indexing...'
  if (status === 'indexed') return 'Indexed'
  if (status === 'failed') return 'Failed'
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
  const [indexingId, setIndexingId] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [details, setDetails] = useState<DocumentDetails | null>(null)
  const [content, setContent] = useState<DocumentContentResponse | null>(null)
  const [chunks, setChunks] = useState<DocumentChunkResponse | null>(null)
  const [contentLoading, setContentLoading] = useState(false)
  const [chunkPage, setChunkPage] = useState(1)

  const handleUnauthorized = useCallback((requestError: unknown): boolean => {
    if (requestError instanceof ApiError && requestError.status === 401) {
      logout(); navigate('/login', { replace: true }); return true
    }
    return false
  }, [logout, navigate])

  const loadDocuments = async () => {
    if (!token) return
    setIsLoading(true)
    try {
      const response = await listDocuments(token)
      setDocuments(response.items); setTotal(response.total)
    } catch (requestError) { if (!handleUnauthorized(requestError)) setError('Unable to load documents.') }
    finally { setIsLoading(false) }
  }

  useEffect(() => {
    if (!token) return
    let cancelled = false
    listDocuments(token).then((response) => {
      if (!cancelled) { setDocuments(response.items); setTotal(response.total) }
    }).catch((requestError: unknown) => {
      if (!cancelled && !handleUnauthorized(requestError)) setError('Unable to load documents.')
    }).finally(() => { if (!cancelled) setIsLoading(false) })
    return () => { cancelled = true }
  }, [token, handleUnauthorized])

  const selectFile = (selected: File | undefined) => {
    setError(''); setSuccess(''); if (!selected) return
    const extension = `.${selected.name.split('.').pop()?.toLowerCase() ?? ''}`
    if (!supportedExtensions.includes(extension)) { setFile(null); setError('Only PDF and DOCX files are supported.'); return }
    if (selected.size === 0) { setFile(null); setError('The selected file is empty.'); return }
    if (selected.size > maxUploadSizeMb * 1024 * 1024) { setFile(null); setError(`Files must be ${maxUploadSizeMb} MB or smaller.`); return }
    setFile(selected)
  }

  const handleUpload = async () => {
    if (!file || !token) { setError('Choose a PDF or DOCX file first.'); return }
    setIsUploading(true); setError(''); setSuccess('')
    try {
      await uploadDocument(token, file, title); setFile(null); setTitle('')
      if (inputRef.current) inputRef.current.value = ''
      setSuccess('Document uploaded. Process it before indexing.'); await loadDocuments()
    } catch (requestError) { if (!handleUnauthorized(requestError)) setError(requestError instanceof ApiError ? requestError.message : 'Unable to upload document.') }
    finally { setIsUploading(false) }
  }

  const handleDetails = async (id: string) => {
    if (!token) return
    try { setDetails(await getDocument(token, id)) }
    catch (requestError) { if (!handleUnauthorized(requestError)) setError('Unable to load document details.') }
  }

  const handleProcess = async (id: string) => {
    if (!token) return
    setProcessingId(id); setError('')
    try {
      const result = await processDocument(token, id)
      if (result.status === 'processed') setSuccess('Document processed successfully.')
      else setError(result.processing_error ?? 'Document processing failed.')
      await loadDocuments(); if (details?.id === id) await handleDetails(id)
    } catch (requestError) { if (!handleUnauthorized(requestError)) setError(requestError instanceof ApiError ? requestError.message : 'Unable to process document.') }
    finally { setProcessingId(null) }
  }

  const handleIndex = async (id: string) => {
    if (!token) return
    setIndexingId(id); setError('')
    try {
      const result = await indexDocument(token, id)
      if (result.status === 'indexed') setSuccess(`Indexed ${result.chunk_count} semantic chunks.`)
      else setError(result.indexing_error ?? 'Document indexing failed.')
      await loadDocuments(); if (details?.id === id) await handleDetails(id)
    } catch (requestError) { if (!handleUnauthorized(requestError)) setError(requestError instanceof ApiError ? requestError.message : 'Unable to index document.') }
    finally { setIndexingId(null) }
  }

  const handleContent = async (id: string) => {
    if (!token) return
    setContentLoading(true)
    try { setContent(await getDocumentContent(token, id)) }
    catch (requestError) { if (!handleUnauthorized(requestError)) setError('Unable to load extracted content.') }
    finally { setContentLoading(false) }
  }

  const handleChunks = async (id: string, page = 1) => {
    if (!token) return
    setContentLoading(true)
    try { setChunks(await getDocumentChunks(token, id, page)); setChunkPage(page) }
    catch (requestError) { if (!handleUnauthorized(requestError)) setError('Unable to load document chunks.') }
    finally { setContentLoading(false) }
  }

  const handleDownload = async (document: DocumentRecord) => {
    if (!token) return
    try {
      const blob = await downloadDocument(token, document.id); const url = URL.createObjectURL(blob)
      const anchor = window.document.createElement('a'); anchor.href = url; anchor.download = document.file_name; anchor.click(); URL.revokeObjectURL(url)
    } catch (requestError) { if (!handleUnauthorized(requestError)) setError('Unable to download document.') }
  }

  const handleDelete = async (document: DocumentRecord) => {
    if (!token || !window.confirm(`Delete “${document.file_name}”?\n\nThis will remove the document and its extracted/indexed data.`)) return
    try { await deleteDocument(token, document.id); setSuccess('Document deleted successfully.'); await loadDocuments() }
    catch (requestError) { if (!handleUnauthorized(requestError)) setError('Unable to delete document.') }
  }

  const actionButton = (document: DocumentRecord) => {
    if (document.status === 'uploaded') return <button className="text-amber-300 hover:text-amber-200" disabled={processingId === document.id} onClick={() => void handleProcess(document.id)}>Process</button>
    if (document.status === 'processing') return <span className="text-amber-300">Processing...</span>
    if (document.status === 'processed') return <button className="text-amber-300 hover:text-amber-200" disabled={indexingId === document.id} onClick={() => void handleIndex(document.id)}>Index</button>
    if (document.status === 'indexing') return <span className="text-amber-300">Indexing...</span>
    if (document.status === 'indexed') return <button className="text-amber-300 hover:text-amber-200" disabled={indexingId === document.id} onClick={() => void handleIndex(document.id)}>Re-index</button>
    return document.indexing_error ? <button className="text-amber-300 hover:text-amber-200" disabled={indexingId === document.id} onClick={() => void handleIndex(document.id)}>Retry index</button> : <button className="text-amber-300 hover:text-amber-200" disabled={processingId === document.id} onClick={() => void handleProcess(document.id)}>Retry process</button>
  }

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => selectFile(event.target.files?.[0])
  const onDrop = (event: DragEvent<HTMLLabelElement>) => { event.preventDefault(); selectFile(event.dataTransfer.files[0]) }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100"><div className="mx-auto max-w-6xl">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">Knowledge workspace</p><h1 className="mt-3 text-3xl font-semibold tracking-tight">Knowledge Base</h1><p className="mt-2 text-slate-400">Upload, process, and locally index enterprise documents.</p></div><button className="self-start rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400 sm:self-auto" onClick={() => navigate('/dashboard')}>Back to dashboard</button></header>
      <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6"><div className="flex flex-col gap-5 lg:flex-row lg:items-end"><label className="flex-1 text-sm font-medium text-slate-200">Document title <span className="font-normal text-slate-500">(optional)</span><input className="mt-2 w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 outline-none focus:border-cyan-400" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Derived from filename when empty" /></label><label className="flex-1 cursor-pointer rounded-lg border border-dashed border-slate-600 bg-slate-950 px-4 py-3 text-sm text-slate-300 hover:border-cyan-400" onDragOver={(event) => event.preventDefault()} onDrop={onDrop}><span className="block truncate">{file ? `${file.name} · ${formatBytes(file.size)}` : 'Choose a PDF or DOCX file'}</span><span className="mt-1 block text-xs text-slate-500">PDF/DOCX · up to {maxUploadSizeMb} MB · processing and indexing are manual</span><input ref={inputRef} className="sr-only" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={onFileChange} /></label><button className="rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50" disabled={!file || isUploading} onClick={() => void handleUpload()}>{isUploading ? 'Uploading...' : 'Upload document'}</button></div>{error && <p className="mt-4 rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-300">{error}</p>}{success && <p className="mt-4 rounded-lg border border-emerald-900/60 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">{success}</p>}</section>
      <section className="mt-8 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900"><div className="flex items-center justify-between border-b border-slate-800 px-6 py-5"><div><h2 className="font-semibold">Documents</h2><p className="mt-1 text-sm text-slate-500">{total} document{total === 1 ? '' : 's'}</p></div></div>{isLoading ? <p className="px-6 py-12 text-center text-slate-400">Loading documents...</p> : documents.length === 0 ? <p className="px-6 py-12 text-center text-slate-400">No knowledge documents uploaded yet.</p> : <div className="overflow-x-auto"><table className="w-full min-w-[980px] text-left text-sm"><thead className="bg-slate-950/50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-6 py-4">Document</th><th className="px-6 py-4">Type</th><th className="px-6 py-4">Size</th><th className="px-6 py-4">Status</th><th className="px-6 py-4">Chunks</th><th className="px-6 py-4">Uploaded</th><th className="px-6 py-4">Actions</th></tr></thead><tbody className="divide-y divide-slate-800">{documents.map((document) => <tr key={document.id} className="text-slate-300"><td className="px-6 py-4"><p className="font-medium text-slate-100">{document.title}</p><p className="mt-1 text-xs text-slate-500">{document.file_name}</p></td><td className="px-6 py-4 uppercase">{document.file_type}</td><td className="px-6 py-4">{formatBytes(document.file_size)}</td><td className="px-6 py-4"><span className="rounded-full bg-cyan-400/10 px-3 py-1 text-xs text-cyan-300">{statusLabel(document.status)}</span></td><td className="px-6 py-4">{document.chunk_count || '—'}</td><td className="px-6 py-4">{formatDate(document.created_at)}</td><td className="px-6 py-4"><div className="flex flex-wrap gap-3"><button className="text-cyan-300 hover:text-cyan-200" onClick={() => void handleDetails(document.id)}>Details</button>{(document.status === 'processed' || document.status === 'indexed') && <button className="text-cyan-300 hover:text-cyan-200" onClick={() => void handleContent(document.id)}>Content</button>}{document.status === 'indexed' && <button className="text-cyan-300 hover:text-cyan-200" onClick={() => void handleChunks(document.id)}>Chunks</button>}{actionButton(document)}<button className="text-slate-300 hover:text-white" onClick={() => void handleDownload(document)}>Download</button><button className="text-red-300 hover:text-red-200" onClick={() => void handleDelete(document)}>Delete</button></div></td></tr>)}</tbody></table></div>}</section>
    </div>
      {details && <div className="fixed inset-0 z-10 flex items-center justify-center bg-slate-950/80 px-6" role="dialog" aria-modal="true"><div className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"><div className="flex items-start justify-between gap-4"><div><p className="text-sm text-cyan-400">Document details</p><h2 className="mt-2 text-2xl font-semibold">{details.title}</h2></div><button className="text-2xl text-slate-400 hover:text-white" onClick={() => setDetails(null)} aria-label="Close details">×</button></div><dl className="mt-6 grid grid-cols-2 gap-5 text-sm"><div><dt className="text-slate-500">Filename</dt><dd className="mt-1 break-words text-slate-200">{details.file_name}</dd></div><div><dt className="text-slate-500">Status</dt><dd className="mt-1 text-slate-200">{statusLabel(details.status)}</dd></div><div><dt className="text-slate-500">Pages</dt><dd className="mt-1 text-slate-200">{details.page_count ?? 'Not available for this format'}</dd></div><div><dt className="text-slate-500">Extracted blocks</dt><dd className="mt-1 text-slate-200">{details.extracted_block_count}</dd></div><div><dt className="text-slate-500">Chunks</dt><dd className="mt-1 text-slate-200">{details.chunk_count}</dd></div><div><dt className="text-slate-500">Embedding model</dt><dd className="mt-1 break-words text-slate-200">{details.embedding_model ?? 'Not configured'}</dd></div><div><dt className="text-slate-500">Vector dimension</dt><dd className="mt-1 text-slate-200">{details.embedding_dimension ?? '—'}</dd></div><div><dt className="text-slate-500">Chunk size</dt><dd className="mt-1 text-slate-200">{details.chunk_size_words ? `${details.chunk_size_words} words` : '—'}</dd></div><div><dt className="text-slate-500">Overlap</dt><dd className="mt-1 text-slate-200">{details.chunk_overlap_words ? `${details.chunk_overlap_words} words` : '—'}</dd></div></dl>{details.processing_error && <p className="mt-5 rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-300">Processing: {details.processing_error}</p>}{details.indexing_error && <p className="mt-5 rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-300">Indexing: {details.indexing_error}</p>}<div className="mt-6 flex flex-wrap gap-3">{details.status === 'processed' && <button className="rounded-lg bg-amber-400 px-4 py-2 font-semibold text-slate-950" onClick={() => void handleIndex(details.id)}>Index document</button>}{details.status === 'indexed' && <><button className="rounded-lg border border-amber-400 px-4 py-2 text-amber-300" onClick={() => void handleIndex(details.id)}>Re-index document</button><button className="rounded-lg border border-cyan-400 px-4 py-2 text-cyan-300" onClick={() => void handleChunks(details.id)}>View chunks</button></>}{(details.status === 'processed' || details.status === 'indexed') && <button className="rounded-lg border border-cyan-400 px-4 py-2 text-cyan-300" onClick={() => void handleContent(details.id)}>View extracted content</button>}</div></div></div>}
      {content && <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-950/80 px-6" role="dialog" aria-modal="true"><div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"><div className="flex items-center justify-between"><div><p className="text-sm text-cyan-400">Extracted content</p><h2 className="mt-2 text-2xl font-semibold">Source blocks</h2></div><button className="text-2xl text-slate-400 hover:text-white" onClick={() => setContent(null)} aria-label="Close extracted content">×</button></div>{contentLoading ? <p className="py-10 text-center text-slate-400">Loading extracted content...</p> : <div className="mt-6 space-y-4">{content.items.map((item) => <article key={item.sequence_index} className="rounded-lg border border-slate-800 bg-slate-950 p-4"><p className="text-xs font-semibold uppercase tracking-wide text-cyan-400">{item.page_number === null ? `Section ${item.sequence_index + 1}` : `Page ${item.page_number}`}</p><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">{item.content}</p></article>)}</div>}</div></div>}
      {chunks && <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-950/80 px-6" role="dialog" aria-modal="true"><div className="max-h-[85vh] w-full max-w-3xl overflow-y-auto rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"><div className="flex items-center justify-between"><div><p className="text-sm text-cyan-400">Indexed chunks</p><h2 className="mt-2 text-2xl font-semibold">Chunk inspection</h2></div><button className="text-2xl text-slate-400 hover:text-white" onClick={() => setChunks(null)} aria-label="Close chunks">×</button></div>{contentLoading ? <p className="py-10 text-center text-slate-400">Loading chunks...</p> : <><div className="mt-6 space-y-4">{chunks.items.map((chunk) => <article key={chunk.id} className="rounded-lg border border-slate-800 bg-slate-950 p-4"><div className="flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-wide text-cyan-400"><span>Chunk {chunk.chunk_index + 1}</span><span>{chunk.page_number === null ? 'Logical section' : `Page ${chunk.page_number}`}</span><span>{chunk.word_count} words</span></div><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-300">{chunk.content}</p></article>)}</div><div className="mt-6 flex items-center justify-between text-sm text-slate-400"><span>Page {chunks.page} of {chunks.total_pages || 1} · {chunks.total} chunks</span><div className="flex gap-2"><button className="rounded border border-slate-700 px-3 py-1 disabled:opacity-40" disabled={chunkPage <= 1} onClick={() => void handleChunks(chunks.document_id, chunkPage - 1)}>Previous</button><button className="rounded border border-slate-700 px-3 py-1 disabled:opacity-40" disabled={chunkPage >= chunks.total_pages} onClick={() => void handleChunks(chunks.document_id, chunkPage + 1)}>Next</button></div></div></>}</div></div>}
    </main>
  )
}
