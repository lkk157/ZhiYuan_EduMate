export const ROLE_LABELS = {
  student: '学生',
  teacher: '教师',
  admin: '管理员',
}

export const ROLE_HOME = {
  student: '/student/home',
  teacher: '/teacher/home',
  admin: '/admin/home',
}

export const ROLE_MENUS = {
  student: [
    { label: '首页', path: '/student/home', icon: 'HomeFilled' },
    { label: '我的课程', path: '/student/courses', icon: 'Notebook' },
    { label: 'AI 学伴问答', path: '/student/qa', icon: 'ChatDotRound' },
    { label: '问答记录', path: '/student/qa-history', icon: 'Clock' },
    { label: '学习资料', path: '/student/materials', icon: 'FolderOpened' },
    { label: '我的知识库', path: '/student/knowledge-bases', icon: 'Files' },
    { label: '习题练习', path: '/student/practice', icon: 'EditPen' },
  ],
  teacher: [
    { label: '教师首页', path: '/teacher/home', icon: 'HomeFilled' },
    { label: '课程管理', path: '/teacher/courses', icon: 'Notebook' },
    { label: '资料上传', path: '/teacher/materials', icon: 'UploadFilled' },
    { label: '学情看板', path: '/teacher/analytics', icon: 'DataAnalysis' },
  ],
  admin: [
    { label: '仪表盘', path: '/admin/home', icon: 'Odometer' },
    { label: '用户管理', path: '/admin/users', icon: 'User' },
    { label: '角色权限', path: '/admin/roles', icon: 'Key' },
    { label: '课程审核', path: '/admin/reviews', icon: 'DocumentChecked' },
    { label: '资料审核', path: '/admin/materials', icon: 'Files' },
    { label: '审计日志', path: '/admin/audit', icon: 'Tickets' },
    { label: '系统配置', path: '/admin/settings', icon: 'Setting' },
  ],
}

export function homePathForRole(role) {
  return ROLE_HOME[role] || '/login'
}

export function menuForRole(role) {
  return ROLE_MENUS[role] || []
}

export function roleLabel(role) {
  return ROLE_LABELS[role] || '用户'
}
