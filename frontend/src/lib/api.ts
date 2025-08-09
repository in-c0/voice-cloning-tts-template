const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function synthesize(form: FormData): Promise<Blob> {
  const res = await fetch(`${API_URL}/api/tts`, { method: 'POST', body: form })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || res.statusText)
  }
  return await res.blob()
}

export async function engines() {
  const res = await fetch(`${API_URL}/api/engines`)
  return await res.json()
}
