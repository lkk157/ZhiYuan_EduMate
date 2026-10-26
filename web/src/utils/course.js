export const COURSE_STATUS_META = {
  draft: { label: '草稿', type: 'info', hint: '完善章节后提交审核' },
  pending: { label: '待审核', type: 'warning', hint: '管理员审核中，内容已锁定' },
  approved: { label: '已发布', type: 'success', hint: '学生可通过邀请码加入' },
  rejected: { label: '已驳回', type: 'danger', hint: '根据审核意见修改后重新提交' },
}

export const ENROLLMENT_SOURCE_LABELS = {
  invite_code: '邀请码加入',
  teacher_add: '教师添加',
}

export function courseStatusLabel(status) {
  return COURSE_STATUS_META[status]?.label || status
}

export function courseStatusType(status) {
  return COURSE_STATUS_META[status]?.type || 'info'
}

export function enrollmentSourceLabel(source) {
  return ENROLLMENT_SOURCE_LABELS[source] || source
}

export function canEditCourse(status) {
  return status === 'draft' || status === 'rejected' || status === 'approved'
}

export function canSubmitCourse(status) {
  return status === 'draft' || status === 'rejected'
}
