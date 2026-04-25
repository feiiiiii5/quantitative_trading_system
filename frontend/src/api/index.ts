import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.warn(`API error: ${error.config?.url}`, error.message)
    return Promise.resolve({ data: { success: false, data: null, error: error.message } })
  }
)

export async function apiGet<T = any>(url: string): Promise<T | null> {
  try {
    const res = await api.get(url)
    const body = res.data
    if (body && typeof body === 'object' && 'success' in body) {
      if (body.success) {
        return (body.data ?? null) as T
      }
      return null
    }
    return body as T
  } catch {
    return null
  }
}

export async function apiPost<T = any>(url: string, data?: any): Promise<T | null> {
  try {
    const res = await api.post(url, data)
    const body = res.data
    if (body && typeof body === 'object' && 'success' in body) {
      if (body.success) {
        return (body.data ?? null) as T
      }
      return null
    }
    return body as T
  } catch {
    return null
  }
}

export { api }
