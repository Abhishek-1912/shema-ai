import type { Source } from '../../types/documents'
import { splitAnswer } from './citations'

interface AnswerTextProps {
  answer: string
  sources: Source[]
  activeNumber: number | null
  onCite: (number: number) => void
}

// The answer with every [n] turned into a small button that shows that source.
function AnswerText({ answer, sources, activeNumber, onCite }: AnswerTextProps) {
  const parts = splitAnswer(answer, new Set(sources.map((s) => s.number)))

  return (
    <p className="whitespace-pre-wrap leading-relaxed">
      {parts.map((part, index) =>
        part.kind === 'text' ? (
          <span key={index}>{part.text}</span>
        ) : (
          <button
            key={index}
            type="button"
            aria-label={`Show source ${part.number}`}
            onClick={() => onCite(part.number)}
            className={`mx-0.5 rounded px-1 align-super text-xs font-semibold ${
              activeNumber === part.number
                ? 'bg-blue-600 text-white'
                : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
            }`}
          >
            {part.number}
          </button>
        ),
      )}
    </p>
  )
}

export default AnswerText
