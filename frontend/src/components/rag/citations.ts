// Turn the "[n]" markers in an answer into parts the UI can render as buttons.

export type AnswerPart = { kind: 'text'; text: string } | { kind: 'citation'; number: number }

// "Return within 30 days [1][2]." → text, citation 1, citation 2, text.
// Only numbers that really exist in the sources become citations; others stay plain text.
export function splitAnswer(answer: string, validNumbers: Set<number>): AnswerPart[] {
  const parts: AnswerPart[] = []
  let last = 0
  for (const match of answer.matchAll(/\[(\d+)\]/g)) {
    const number = Number(match[1])
    if (!validNumbers.has(number)) continue
    if (match.index > last) parts.push({ kind: 'text', text: answer.slice(last, match.index) })
    parts.push({ kind: 'citation', number })
    last = match.index + match[0].length
  }
  if (last < answer.length) parts.push({ kind: 'text', text: answer.slice(last) })
  return parts
}
