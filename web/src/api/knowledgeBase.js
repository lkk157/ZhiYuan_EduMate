import http from './http'

export function listKnowledgeBases() {
  return http.get('/knowledge-bases')
}

export function createKnowledgeBase(payload) {
  return http.post('/knowledge-bases', payload)
}

export function updateKnowledgeBase(kbId, payload) {
  return http.put(`/knowledge-bases/${kbId}`, payload)
}

export function deleteKnowledgeBase(kbId) {
  return http.delete(`/knowledge-bases/${kbId}`)
}

export function listKnowledgeBaseMaterials(kbId, params) {
  return http.get(`/knowledge-bases/${kbId}/materials`, { params })
}

export function uploadKnowledgeBaseMaterial(kbId, file, options = {}) {
  const form = new FormData()
  form.append('file', file)
  if (options.title) form.append('title', options.title)
  return http.post(`/knowledge-bases/${kbId}/materials`, form)
}

export function deleteKnowledgeBaseMaterial(kbId, materialId) {
  return http.delete(`/knowledge-bases/${kbId}/materials/${materialId}`)
}

export function retryKnowledgeBaseMaterial(kbId, materialId) {
  return http.post(`/knowledge-bases/${kbId}/materials/${materialId}/index/retry`)
}
