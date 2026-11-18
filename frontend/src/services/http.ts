// Shared HTTP helpers for every API client (chat, documents, ...).

// An error with a message that is safe and useful to show to the user.
export class ApiError extends Error {
  readonly status: number | null

  constructor(message: string, status: number | null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// Do the request and turn every kind of failure into an ApiError.
export async function send(url: string, init?: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch {
    // fetch itself only throws when no HTTP response arrived at all (network down).
    throw new ApiError('Cannot reach the Shema AI server. Is the backend running?', null)
  }

  if (!response.ok) {
    throw new ApiError(await readErrorMessage(response), response.status)
  }
  return response
}

// Never trust data from the network: check it really has the shape we expect.
export async function readJson<T>(
  response: Response,
  isValid: (data: unknown) => data is T,
): Promise<T> {
  const data: unknown = await response.json().catch(() => null)
  if (!isValid(data)) {
    throw new ApiError('The server sent an unexpected response.', response.status)
  }
  return data
}

export function isObject(data: unknown): data is Record<string, unknown> {
  return typeof data === 'object' && data !== null
}

// FastAPI errors look like {"detail": "..."}. Use that text when it exists.
async function readErrorMessage(response: Response): Promise<string> {
  const data: unknown = await response.json().catch(() => null)
  if (isObject(data) && typeof data.detail === 'string') {
    return data.detail
  }
  if (response.status >= 500) {
    return `The server had a problem (error ${response.status}). Is the backend running?`
  }
  return `The request failed (error ${response.status}).`
}
