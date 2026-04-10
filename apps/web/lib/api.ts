/**
 * Shared API client for all frontend requests
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface ApiError {
  status: number
  message: string
  details?: string
}

export class ApiRequestError extends Error implements ApiError {
  status: number
  details?: string

  constructor({ status, message, details }: ApiError) {
    super(message)
    this.name = "ApiRequestError"
    this.status = status
    this.details = details
  }
}

function isApiError(value: unknown): value is ApiError {
  if (!value || typeof value !== "object") {
    return false
  }

  const candidate = value as Partial<ApiError>
  return typeof candidate.status === "number" && typeof candidate.message === "string"
}

function buildNetworkError(url: string, error: unknown): ApiRequestError {
  const details =
    error instanceof Error ? error.message : typeof error === "string" ? error : String(error)

  return new ApiRequestError({
    status: 0,
    message: `Unable to reach API server at ${API_URL}. Make sure the API is running and that CORS allows the current web origin.`,
    details: `${url} :: ${details}`,
  })
}

export async function apiGet<T>(endpoint: string): Promise<T> {
  const url = `${API_URL}${endpoint}`
  console.log(`[API] GET ${url}`)

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    })

    if (!response.ok) {
      const error: ApiError = {
        status: response.status,
        message: `HTTP ${response.status}: ${response.statusText}`,
      }
      try {
        const errorBody = await response.json()
        error.details = JSON.stringify(errorBody)
      } catch {
        // Ignore JSON parse errors
      }
      throw new ApiRequestError(error)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error
    }
    if (isApiError(error)) {
      throw new ApiRequestError(error)
    }
    throw buildNetworkError(url, error)
  }
}

export async function apiPost<T>(endpoint: string, body?: unknown): Promise<T> {
  const url = `${API_URL}${endpoint}`
  console.log(`[API] POST ${url}`, body)

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!response.ok) {
      const error: ApiError = {
        status: response.status,
        message: `HTTP ${response.status}: ${response.statusText}`,
      }
      try {
        const errorBody = await response.json()
        error.details = JSON.stringify(errorBody)
      } catch {
        // Ignore JSON parse errors
      }
      throw new ApiRequestError(error)
    }

    return await response.json()
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error
    }
    if (isApiError(error)) {
      throw new ApiRequestError(error)
    }
    throw buildNetworkError(url, error)
  }
}
