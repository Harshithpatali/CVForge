const API_BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    credentials: 'include',
    ...options,
  })
  const contentType = response.headers.get('content-type') || ''
  if (!response.ok) {
    let message = 'Request failed'
    if (contentType.includes('application/json')) {
      const body = await response.json().catch(() => null)
      message = body?.detail || body?.message || message
    } else {
      message = await response.text().catch(() => message)
    }
    throw new Error(message)
  }
  return contentType.includes('application/json') ? response.json() : response
}

export const health = () => request('/health')

export async function analyzeAndGenerate({ jobDescription, cvText, cvFile }) {
  const form = new FormData()
  form.append('jd', jobDescription)
  form.append('cv_text', cvText || '')
  if (cvFile) form.append('cv', cvFile)
  return request('/v1/jobs/analyze', { method: 'POST', body: form })
}