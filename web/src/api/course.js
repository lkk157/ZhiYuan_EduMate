import http from './http'

export function listCourses(params) {
  return http.get('/courses', { params })
}

export function getCourse(courseId) {
  return http.get(`/courses/${courseId}`)
}

export function createCourse(payload) {
  return http.post('/courses', payload)
}

export function updateCourse(courseId, payload) {
  return http.put(`/courses/${courseId}`, payload)
}

export function submitCourse(courseId) {
  return http.post(`/courses/${courseId}/submit`)
}

export function reviewCourse(courseId, payload) {
  return http.post(`/courses/${courseId}/review`, payload)
}

export function rotateInvite(courseId) {
  return http.post(`/courses/${courseId}/invite/rotate`)
}

export function toggleInvite(courseId, enabled) {
  return http.put(`/courses/${courseId}/invite`, { enabled })
}

export function joinCourse(inviteCode) {
  return http.post('/courses/join', { invite_code: inviteCode })
}

export function listCourseStudents(courseId, params) {
  return http.get(`/courses/${courseId}/students`, { params })
}

export function addStudent(courseId, username) {
  return http.post(`/courses/${courseId}/students`, { username })
}

export function removeStudent(courseId, studentId) {
  return http.delete(`/courses/${courseId}/students/${studentId}`)
}

export function createChapter(courseId, payload) {
  return http.post(`/courses/${courseId}/chapters`, payload)
}

export function updateChapter(courseId, chapterId, payload) {
  return http.put(`/courses/${courseId}/chapters/${chapterId}`, payload)
}

export function deleteChapter(courseId, chapterId) {
  return http.delete(`/courses/${courseId}/chapters/${chapterId}`)
}

export function createKnowledge(courseId, chapterId, payload) {
  return http.post(`/courses/${courseId}/chapters/${chapterId}/knowledges`, payload)
}

export function updateKnowledge(courseId, chapterId, knowledgeId, payload) {
  return http.put(
    `/courses/${courseId}/chapters/${chapterId}/knowledges/${knowledgeId}`,
    payload,
  )
}

export function deleteKnowledge(courseId, chapterId, knowledgeId) {
  return http.delete(
    `/courses/${courseId}/chapters/${chapterId}/knowledges/${knowledgeId}`,
  )
}
