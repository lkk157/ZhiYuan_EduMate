import http from './http'

export function getStudentHome() {
  return http.get('/home/overview')
}

export function listRecommendations(params) {
  return http.get('/recommendations', { params })
}
