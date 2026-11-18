import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../services/http'
import { deleteDocument, listDocuments, uploadDocument } from '../services/documentsApi'
import { ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, type DocumentSummary } from '../types/documents'

const GENERIC_ERROR = 'Something went wrong. Please try again.'

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : GENERIC_ERROR
}

// Check the file in the browser first: instant feedback, no wasted upload.
// The backend checks again (never trust the browser alone).
export function validateFile(file: File): string | null {
  const name = file.name.toLowerCase()
  if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return `"${file.name}" is not supported. Use PDF, Word (.docx), TXT or Markdown.`
  }
  if (file.size === 0) return `"${file.name}" is empty.`
  if (file.size > MAX_UPLOAD_BYTES) return `"${file.name}" is larger than 10 MB.`
  return null
}

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null) // success message

  const refresh = useCallback(async () => {
    try {
      setDocuments((await listDocuments()).documents)
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [])

  // Load the list once. State is set in promise callbacks (React hooks lint rule).
  useEffect(() => {
    let ignore = false
    listDocuments()
      .then((data) => {
        if (!ignore) setDocuments(data.documents)
      })
      .catch((err: unknown) => {
        if (!ignore) setError(errorMessage(err))
      })
      .finally(() => {
        if (!ignore) setIsLoading(false)
      })
    return () => {
      ignore = true
    }
  }, [])

  async function upload(file: File, title?: string): Promise<boolean> {
    setError(null)
    setNotice(null)
    const problem = validateFile(file)
    if (problem) {
      setError(problem)
      return false
    }

    setIsUploading(true)
    try {
      const result = await uploadDocument(file, title)
      setNotice(
        `"${result.title}" is ready: ${result.page_count} page(s), ${result.chunk_count} searchable chunks.`,
      )
      await refresh()
      return true
    } catch (err) {
      setError(errorMessage(err))
      return false
    } finally {
      setIsUploading(false)
    }
  }

  async function remove(id: string): Promise<boolean> {
    setError(null)
    setNotice(null)
    try {
      await deleteDocument(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
      return true
    } catch (err) {
      setError(errorMessage(err))
      return false
    }
  }

  return { documents, isLoading, isUploading, error, notice, upload, remove }
}
