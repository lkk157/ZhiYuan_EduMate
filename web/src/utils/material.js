export const MATERIAL_STATUS_META = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
  deleted: { label: '已删除', type: 'info' },
}

export const INDEX_STATUS_META = {
  pending: { label: '待索引', type: 'info' },
  indexing: { label: '索引中', type: 'warning' },
  indexed: { label: '已索引', type: 'success' },
  failed: { label: '索引失败', type: 'danger' },
}

export function materialStatusLabel(status) {
  return MATERIAL_STATUS_META[status]?.label || status
}

export function materialStatusType(status) {
  return MATERIAL_STATUS_META[status]?.type || 'info'
}

export function indexStatusLabel(status) {
  return INDEX_STATUS_META[status]?.label || status
}

export function indexStatusType(status) {
  return INDEX_STATUS_META[status]?.type || 'info'
}

export function formatFileSize(bytes) {
  const size = Number(bytes || 0)
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
}

export function fileTypeLabel(type) {
  return String(type || '').replace('.', '').toUpperCase()
}
