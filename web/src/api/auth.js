import http from './http'

export function login(payload) {
  return http.post('/auth/login', payload)
}

export function register(payload) {
  return http.post('/auth/register', payload)
}

export function fetchMe() {
  return http.get('/auth/me')
}

export function changePassword(payload) {
  return http.put('/auth/password', payload)
}
