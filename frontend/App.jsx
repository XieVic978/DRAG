import { useCallback, useEffect, useRef, useState } from 'react'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function requestDocuments() {
  const response = await fetch(`${API_URL}/documents`)
  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || 'Could not load the document library.')
  }
  return data
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const unitIndex = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  )
  const value = bytes / 1024 ** unitIndex
  return `${value.toFixed(unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}

function sourceLabel(source) {
  return `${source.filename}${source.page ? ` · page ${source.page}` : ''}`
}

function App() {
  const [documents, setDocuments] = useState([])
  const [indexedChunkCount, setIndexedChunkCount] = useState(0)
  const [selectedFiles, setSelectedFiles] = useState([])
  const [uploadResults, setUploadResults] = useState([])
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState([])
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [loadingDocuments, setLoadingDocuments] = useState(true)
  const [deletingId, setDeletingId] = useState('')
  const fileInputRef = useRef(null)

  const loadDocuments = useCallback(async () => {
    try {
      const data = await requestDocuments()
      setDocuments(data.documents)
      setIndexedChunkCount(data.indexed_chunk_count)
    } catch (loadError) {
      setError(loadError.message)
    } finally {
      setLoadingDocuments(false)
    }
  }, [])

  useEffect(() => {
    let active = true

    requestDocuments()
      .then((data) => {
        if (active) {
          setDocuments(data.documents)
          setIndexedChunkCount(data.indexed_chunk_count)
        }
      })
      .catch((loadError) => {
        if (active) setError(loadError.message)
      })
      .finally(() => {
        if (active) setLoadingDocuments(false)
      })

    return () => {
      active = false
    }
  }, [])

  async function handleUpload(event) {
    event.preventDefault()
    if (selectedFiles.length === 0) {
      setError('Choose at least one PDF, TXT, or CSV file.')
      return
    }

    const formData = new FormData()
    selectedFiles.forEach((file) => formData.append('files', file))

    setUploading(true)
    setError('')
    setUploadResults([])

    try {
      const response = await fetch(`${API_URL}/documents`, {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'The upload failed.')
      }

      setUploadResults(data.documents)
      setSelectedFiles([])
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      await loadDocuments()
    } catch (uploadError) {
      setError(uploadError.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleQuestion(event) {
    event.preventDefault()
    const cleanedQuestion = question.trim()
    if (!cleanedQuestion) {
      setError('Enter a question first.')
      return
    }

    setSearching(true)
    setError('')
    setAnswer('')
    setSources([])

    try {
      const response = await fetch(`${API_URL}/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: cleanedQuestion,
          top_k: 5,
        }),
      })
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'The search failed.')
      }
      setAnswer(data.answer)
      setSources(data.sources || [])
    } catch (searchError) {
      setError(searchError.message)
    } finally {
      setSearching(false)
    }
  }

  async function handleDelete(document) {
    const confirmed = window.confirm(
      `Remove “${document.filename}” from the document library?`,
    )
    if (!confirmed) return

    setDeletingId(document.document_id)
    setError('')

    try {
      const response = await fetch(
        `${API_URL}/documents/${document.document_id}`,
        { method: 'DELETE' },
      )
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Could not delete the document.')
      }
      setDocuments((current) =>
        current.filter((item) => item.document_id !== document.document_id),
      )
      setIndexedChunkCount((current) =>
        Math.max(0, current - data.removed_chunks),
      )
    } catch (deleteError) {
      setError(deleteError.message)
    } finally {
      setDeletingId('')
    }
  }

  const readyDocuments = documents.filter(
    (document) => document.status === 'ready',
  )

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <p className="eyebrow">Private knowledge workspace</p>
          <h1>Ask your documents</h1>
          <p className="intro">
            Add your files, then ask questions grounded in their contents.
          </p>
        </div>
        <div className="library-count" aria-label="Ready document count">
          <strong>{readyDocuments.length}</strong>
          <span>{readyDocuments.length === 1 ? 'document' : 'documents'}</span>
        </div>
      </header>

      {error && (
        <div className="alert error-alert" role="alert">
          {error}
        </div>
      )}

      <div className="workspace-grid">
        <section className="panel upload-panel">
          <div className="panel-heading">
            <div>
              <p className="step-label">Step 1</p>
              <h2>Build your library</h2>
            </div>
            <span className="file-hint">PDF · TXT · CSV</span>
          </div>

          <form onSubmit={handleUpload}>
            <label className="file-drop">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.csv"
                multiple
                onChange={(event) =>
                  setSelectedFiles(Array.from(event.target.files))
                }
              />
              <span className="upload-icon" aria-hidden="true">↑</span>
              <strong>Choose one or more files</strong>
              <small>Up to 20 MB per file and 50 files per batch</small>
            </label>

            {selectedFiles.length > 0 && (
              <ul className="selected-files" aria-label="Files selected to upload">
                {selectedFiles.map((file) => (
                  <li key={`${file.name}-${file.lastModified}`}>
                    <span>{file.name}</span>
                    <small>{formatBytes(file.size)}</small>
                  </li>
                ))}
              </ul>
            )}

            <button
              className="primary-button"
              type="submit"
              disabled={uploading || selectedFiles.length === 0}
            >
              {uploading
                ? 'Reading and indexing…'
                : `Upload${selectedFiles.length ? ` ${selectedFiles.length}` : ''}`}
            </button>
          </form>

          {uploadResults.length > 0 && (
            <div className="upload-results" aria-live="polite">
              {uploadResults.map((result, index) => (
                <p
                  key={`${result.document_id || result.filename}-${index}`}
                  className={`result-${result.status}`}
                >
                  <strong>{result.filename}</strong>
                  <span>
                    {result.status === 'ready' &&
                      `Ready · ${result.chunk_count} chunks`}
                    {result.status === 'duplicate' &&
                      (result.message || 'Already uploaded')}
                    {result.status === 'failed' && result.error}
                  </span>
                </p>
              ))}
            </div>
          )}

          <div className="document-library">
            <div className="library-heading">
              <h3>Your documents</h3>
              <button
                className="text-button"
                type="button"
                onClick={loadDocuments}
                disabled={loadingDocuments}
              >
                Refresh
              </button>
            </div>

            {loadingDocuments ? (
              <p className="empty-state">Loading documents…</p>
            ) : documents.length === 0 ? (
              <p className="empty-state">
                No uploaded documents yet. Add your first file above.
              </p>
            ) : (
              <ul className="document-list">
                {documents.map((document) => (
                  <li key={document.document_id}>
                    <div className="document-icon" aria-hidden="true">
                      {document.filename.split('.').pop()?.toUpperCase()}
                    </div>
                    <div className="document-details">
                      <strong title={document.filename}>{document.filename}</strong>
                      <small>
                        {formatBytes(document.file_size)}
                        {document.status === 'ready' &&
                          ` · ${document.chunk_count} chunks`}
                        {document.status !== 'ready' && ` · ${document.status}`}
                      </small>
                      {document.error && (
                        <span className="document-error">{document.error}</span>
                      )}
                    </div>
                    <button
                      className="delete-button"
                      type="button"
                      onClick={() => handleDelete(document)}
                      disabled={deletingId === document.document_id}
                      aria-label={`Delete ${document.filename}`}
                    >
                      {deletingId === document.document_id ? '…' : '×'}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <section className="panel question-panel">
          <div className="panel-heading">
            <div>
              <p className="step-label">Step 2</p>
              <h2>Ask a question</h2>
            </div>
          </div>

          <form onSubmit={handleQuestion}>
            <label htmlFor="question">What would you like to know?</label>
            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="For example: What are the main conclusions across these documents?"
              rows="6"
            />
            <button
              className="primary-button"
              type="submit"
              disabled={searching || indexedChunkCount === 0}
            >
              {searching ? 'Searching your documents…' : 'Ask question'}
            </button>
            {indexedChunkCount === 0 && (
              <small className="button-help">
                Upload a document before asking a question.
              </small>
            )}
          </form>

          {answer && (
            <article className="answer-card" aria-live="polite">
              <p className="answer-label">Answer</p>
              <div className="answer-text">{answer}</div>

              {sources.length > 0 && (
                <div className="sources">
                  <h3>Retrieved sources</h3>
                  <ul>
                    {sources.map((source, index) => (
                      <li
                        key={`${source.document_id || source.filename}-${source.page || index}`}
                      >
                        {sourceLabel(source)}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </article>
          )}
        </section>
      </div>
    </main>
  )
}

export default App
