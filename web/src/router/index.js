import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { homePathForRole } from '@/utils/roles'

const routes = [
  {
    path: '/login',
    component: () => import('@/layouts/AuthLayout.vue'),
    children: [
      {
        path: '',
        name: 'login',
        component: () => import('@/views/LoginView.vue'),
        meta: { title: '登录', public: true },
      },
    ],
  },
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/student',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true, role: 'student' },
    children: [
      {
        path: 'home',
        name: 'student-home',
        component: () => import('@/views/student/HomeView.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'courses',
        component: () => import('@/views/student/CoursesView.vue'),
        meta: { title: '我的课程' },
      },
      {
        path: 'courses/:id',
        component: () => import('@/views/student/CourseDetailView.vue'),
        meta: { title: '课程详情' },
      },
      {
        path: 'courses/:courseId/chapters/:chapterId',
        name: 'student-chapter',
        component: () => import('@/views/student/ChapterMaterialsView.vue'),
        meta: { title: '章节资料' },
      },
      {
        path: 'qa',
        component: () => import('@/views/student/QaView.vue'),
        meta: { title: 'AI 学伴问答' },
      },
      {
        path: 'qa-history',
        component: () => import('@/views/student/QaHistoryView.vue'),
        meta: { title: '问答记录' },
      },
      {
        path: 'materials',
        component: () => import('@/views/student/MaterialsView.vue'),
        meta: { title: '学习资料' },
      },
      {
        path: 'knowledge-bases',
        component: () => import('@/views/student/KnowledgeBasesView.vue'),
        meta: { title: '我的知识库' },
      },
      {
        path: 'practice',
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '习题练习', description: '习题与答题将在阶段二接入。' },
      },
    ],
  },
  {
    path: '/teacher',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true, role: 'teacher' },
    children: [
      {
        path: 'home',
        name: 'teacher-home',
        component: () => import('@/views/teacher/HomeView.vue'),
        meta: { title: '教师首页' },
      },
      {
        path: 'courses',
        component: () => import('@/views/teacher/CoursesView.vue'),
        meta: { title: '课程管理' },
      },
      {
        path: 'courses/:id',
        component: () => import('@/views/teacher/CourseEditorView.vue'),
        meta: { title: '课程编辑' },
      },
      {
        path: 'materials',
        component: () => import('@/views/teacher/MaterialsView.vue'),
        meta: { title: '资料上传' },
      },
      {
        path: 'analytics',
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '学情看板', description: '学情分析将在阶段二接入。' },
      },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/MainLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      {
        path: 'home',
        name: 'admin-home',
        component: () => import('@/views/admin/HomeView.vue'),
        meta: { title: '仪表盘' },
      },
      {
        path: 'users',
        component: () => import('@/views/admin/UsersView.vue'),
        meta: { title: '用户管理' },
      },
      {
        path: 'roles',
        component: () => import('@/views/admin/RolesView.vue'),
        meta: { title: '角色权限' },
      },
      {
        path: 'reviews',
        component: () => import('@/views/admin/ReviewsView.vue'),
        meta: { title: '课程审核' },
      },
      {
        path: 'materials',
        component: () => import('@/views/admin/MaterialReviewsView.vue'),
        meta: { title: '资料审核' },
      },
      {
        path: 'audit',
        component: () => import('@/views/admin/AuditView.vue'),
        meta: { title: '审计日志' },
      },
      {
        path: 'settings',
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '系统配置', description: '系统配置将在阶段二接入。' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true, title: '页面不存在' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  const title = to.meta?.title
  document.title = title ? `${title} · 智课学伴 EduMate` : '智课学伴 EduMate'

  if (to.meta?.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && auth.isAuthenticated) {
    return homePathForRole(auth.role)
  }

  const requiredRole = to.matched.find((record) => record.meta?.role)?.meta.role
  if (requiredRole && auth.isAuthenticated && auth.role !== requiredRole) {
    return homePathForRole(auth.role)
  }

  return true
})

export default router
