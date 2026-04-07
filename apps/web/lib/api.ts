/**
 * Shared API client for all frontend requests
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export interface ApiError {
  status: number
  message: string
  details?: string
}

function isApiError(value: unknown): value is ApiError {
  if (!value || typeof value !== "object") {
    return false
  }

  const candidate = value as Partial<ApiError>
  return typeof candidate.status === "number" && typeof candidate.message === "string"
}

export async function apiGet<T>(endpoint: string): Promise<T> {
  const url = `${API_URL}${endpoint}`
  console.log(`[API] GET ${url}`)

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
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
      throw error
    }

    return await response.json()
  } catch (error) {
    if (isApiError(error)) {
      throw error
    }
    throw {
      status: 0,
      message: error instanceof Error ? error.message : "Unknown error",
      details: String(error),
    } as ApiError
  }
}

export async function apiPost<T>(endpoint: string, body?: unknown): Promise<T> {
  const url = `${API_URL}${endpoint}`
  console.log(`[API] POST ${url}`, body)

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
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
      throw error
    }

    return await response.json()
  } catch (error) {
    if (isApiError(error)) {
      throw error
    }
    throw {
      status: 0,
      message: error instanceof Error ? error.message : "Unknown error",
      details: String(error),
    } as ApiError
  }
}
