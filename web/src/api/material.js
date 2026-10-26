import http from './http'

export function listMaterials(params) {
  return http.get('/materials', { params })
}

export function getMaterial(materialId) {
  return http.get(`/materials/${materialId}`)
}

export function uploadMaterial(courseId, file, options = {}) {
  const form = new FormData()
  form.append('course_id', String(courseId))
  form.append('file', file)
  if (options.title) form.append('title', options.title)
  if (options.chapterId) form.append('chapter_id', String(options.chapterId))
  if (options.knowledgeId) form.append('knowledge_id', String(options.knowledgeId))
  return http.post('/materials', form)
}

export function uploadMaterialsBatch(courseId, files, options = {}) {
  const form = new FormData()
  form.append('course_id', String(courseId))
  files.forEach((file) => form.append('files', file))
  if (options.title) form.append('title', options.title)
  if (options.chapterId) form.append('chapter_id', String(options.chapterId))
  if (options.knowledgeId) form.append('knowledge_id', String(options.knowledgeId))
  return http.post('/materials/batch', form)
}

export function reviewMaterial(materialId, payload) {
  return http.post(`/materials/${materialId}/review`, payload)
}

export function updateMaterialMapping(materialId, payload) {
  return http.put(`/materials/${materialId}/mapping`, payload)
}

export function retryMaterialIndex(materialId) {
  return http.post(`/materials/${materialId}/index/retry`)
}

export function deleteMaterial(materialId) {
  return http.delete(`/materials/${materialId}`)
}

export function downloadMaterial(materialId) {
  return http.get(`/materials/${materialId}/download`, { responseType: 'blob' })
}

export function markMaterialViewed(materialId) {
  return http.post(`/materials/${materialId}/view`)
}

export function fetchRagHealth() {
  return http.get('/materials/rag-health')
}
