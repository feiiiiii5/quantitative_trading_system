import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios';

const MAX_RETRIES = 3;
const RETRY_BASE_DELAY = 1000;

interface RetryConfig extends InternalAxiosRequestConfig {
  __retryCount?: number;
}

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 15_000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (response) => {
    const payload = response.data;
    if (payload && typeof payload === 'object' && 'success' in payload) {
      if (payload.success) {
        response.data = 'data' in payload ? payload.data : null;
      } else {
        return Promise.reject(new Error(payload.error ?? 'API request failed'));
      }
    }
    return response;
  },
  async (error: AxiosError) => {
    const config = error.config as RetryConfig | undefined;
    if (!config) return Promise.reject(error);

    const isRetryable =
      config.method === 'get' &&
      !axios.isCancel(error) &&
      (error.code === 'ERR_NETWORK' || (error.response?.status ?? 0) >= 500);

    if (isRetryable) {
      const retryCount = config.__retryCount ?? 0;
      if (retryCount < MAX_RETRIES) {
        config.__retryCount = retryCount + 1;
        const delay = RETRY_BASE_DELAY * Math.pow(2, retryCount);
        await new Promise(r => setTimeout(r, delay));
        return apiClient.request(config);
      }
    }

    return Promise.reject(error);
  },
);

export async function apiGet<T>(url: string, params?: Record<string, unknown>, timeout?: number): Promise<T> {
  const res = await apiClient.get<T>(url, { params, timeout });
  return res.data;
}

export async function apiPost<T>(url: string, data?: unknown, timeout?: number): Promise<T> {
  const res = await apiClient.post<T>(url, data, { timeout });
  return res.data;
}
