import http from './http'

export function fetchAdminStats() {
  return http.get('/admin/stats')
}

export function fetchReviewPolicy() {
  return http.get('/admin/review-policy')
}

export function listUsers(params) {
  return http.get('/admin/users', { params })
}

export function createUser(payload) {
  return http.post('/admin/users', payload)
}

export function updateUser(userId, payload) {
  return http.put(`/admin/users/${userId}`, payload)
}

export function setUserStatus(userId, status) {
  return http.put(`/admin/users/${userId}/status`, { status })
}

export function resetUserPassword(userId, newPassword) {
  return http.post(`/admin/users/${userId}/reset-password`, {
    new_password: newPassword,
  })
}

export function fetchRoleOverview() {
  return http.get('/admin/roles')
}

export function listAuditLogs(params) {
  return http.get('/admin/audit-logs', { params })
}
