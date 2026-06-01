/**
 * Simple request wrapper for uni-app style HTTP.
 * In production this wraps uni.request; for this module it exposes
 * a typed interface that pages/components should use.
 */

const BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8001'

interface RequestOptions {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
  header?: Record<string, string>
}

function makeRequest(options: RequestOptions): Promise<any> {
  return new Promise((resolve, reject) => {
    // uni.request wrapper
    const xhr = {
      url: BASE_URL + options.url,
      method: options.method,
      data: options.data,
      header: { 'Content-Type': 'application/json', ...options.header },
      success: (res: any) => resolve(res.data),
      fail: (err: any) => reject(err),
    }
    // @ts-ignore - uni global
    if (typeof uni !== 'undefined') {
      uni.request(xhr)
    } else {
      // fallback for non-uni environment
      fetch(xhr.url, {
        method: xhr.method,
        headers: xhr.header,
        body: xhr.data ? JSON.stringify(xhr.data) : undefined,
      })
        .then(r => r.json())
        .then(resolve)
        .catch(reject)
    }
  })
}

export const request = {
  get(url: string, data?: any) {
    return makeRequest({ url, method: 'GET', data })
  },
  post(url: string, data?: any) {
    return makeRequest({ url, method: 'POST', data })
  },
  put(url: string, data?: any) {
    return makeRequest({ url, method: 'PUT', data })
  },
  delete(url: string, data?: any) {
    return makeRequest({ url, method: 'DELETE', data })
  },
}
