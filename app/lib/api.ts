export const API_URL = 'http://localhost:5000'

export const apiFetch = (path: string, options?: RequestInit) => {
  return fetch(`${API_URL}${path}`, options)
}


