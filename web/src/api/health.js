import http from './http'

export function getReadiness() {
  // Readiness returns 503 when the database is down, but the body still
  // contains per-component status, so accept non-2xx responses here.
  return http.get('/health/ready', { validateStatus: () => true })
}
