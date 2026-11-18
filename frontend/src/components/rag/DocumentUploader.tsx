import { useRef, useState } from 'react'
import { ALLOWED_EXTENSIONS } from '../../types/documents'

interface DocumentUploaderProps {
  onUpload: (file: File, title?: string) => Promise<boolean>
  isUploading: boolean
}

// Drag a file onto the box, or click to choose one. An optional title can be typed first.
function DocumentUploader({ onUpload, isUploading }: DocumentUploaderProps) {
  const [title, setTitle] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleFile(file: File | undefined) {
    if (!file || isUploading) return
    const ok = await onUpload(file, title)
    if (ok) setTitle('')
    if (inputRef.current) inputRef.current.value = '' // allow choosing the same file again
  }

  return (
    <div className="space-y-2">
      <input
        type="text"
        value={title}
        onChange={(event) => setTitle(event.target.value)}
        placeholder="Title (optional)"
        aria-label="Document title"
        className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
      />
      <label
        onDragOver={(event) => {
          event.preventDefault() // needed, otherwise the browser opens the file instead
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(event) => {
          event.preventDefault()
          setIsDragging(false)
          void handleFile(event.dataTransfer.files[0])
        }}
        className={`flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed px-4 py-6 text-center text-sm ${
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-blue-400'
        } ${isUploading ? 'pointer-events-none opacity-60' : ''}`}
      >
        <span className="font-medium text-slate-700">
          {isUploading ? 'Reading, chunking and embedding…' : 'Drop a file here or click to choose'}
        </span>
        <span className="mt-1 text-xs text-slate-500">PDF, Word (.docx), TXT, Markdown · max 10 MB</span>
        <input
          ref={inputRef}
          type="file"
          aria-label="Choose a document"
          accept={ALLOWED_EXTENSIONS.join(',')}
          disabled={isUploading}
          onChange={(event) => void handleFile(event.target.files?.[0])}
          className="sr-only"
        />
      </label>
    </div>
  )
}

export default DocumentUploader
