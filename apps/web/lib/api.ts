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
    message: `无法连接 API 服务：${API_URL}。请确认 API 已启动；如果页面能加载但点击操作时报错，通常是跨域预检被浏览器拦截了。`,
    details: `${url} :: ${details}`,
  })
}

function extractApiErrorMessage(errorBody: unknown): string | null {
  if (!errorBody || typeof errorBody !== "object") {
    return null
  }

  const candidate = errorBody as { detail?: unknown; message?: unknown }
  if (typeof candidate.detail === "string" && candidate.detail.trim()) {
    return candidate.detail
  }
  if (Array.isArray(candidate.detail)) {
    const messages = candidate.detail
      .map((item) => {
        if (typeof item === "string") {
          return item
        }
        if (item && typeof item === "object" && "msg" in item) {
          const msg = (item as { msg?: unknown }).msg
          return typeof msg === "string" ? msg : null
        }
        return null
      })
      .filter((item): item is string => Boolean(item && item.trim()))
    if (messages.length > 0) {
      return messages.join("; ")
    }
  }
  if (typeof candidate.message === "string" && candidate.message.trim()) {
    return candidate.message
  }
  return null
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
        error.message = extractApiErrorMessage(errorBody) ?? error.message
        error.details = JSON.stringify(errorBody)
      } catch {
        // Ignore JSON parse errors.
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
    const headers: Record<string, string> = {
      Accept: "application/json",
    }
    let serializedBody: string | undefined

    if (body !== undefined) {
      headers["Content-Type"] = "application/json"
      serializedBody = JSON.stringify(body)
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: serializedBody,
    })

    if (!response.ok) {
      const error: ApiError = {
        status: response.status,
        message: `HTTP ${response.status}: ${response.statusText}`,
      }
      try {
        const errorBody = await response.json()
        error.message = extractApiErrorMessage(errorBody) ?? error.message
        error.details = JSON.stringify(errorBody)
      } catch {
        // Ignore JSON parse errors.
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
