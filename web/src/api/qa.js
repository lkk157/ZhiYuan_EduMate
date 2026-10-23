import http from './http'

export function askQuestion(payload) {
  return http.post('/qa/ask', payload)
}

export function listQaHistory(params) {
  return http.get('/qa/history', { params })
}
