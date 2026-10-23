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
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '我的课程', description: '课程列表与课程详情将在 P1.4 接入。' },
      },
      {
        path: 'qa',
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: 'AI 学伴问答', description: '带引用的 RAG 问答将在 P1.6 接入。' },
      },
      {
        path: 'qa-history',
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '问答记录', description: '问答历史将在 P1.6 接入。' },
      },
      {
        path: 'materials',
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '学习资料', description: '资料浏览与推荐将在 P1.5 / P1.7 接入。' },
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
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '课程管理', description: '建课、章节与知识点管理将在 P1.4 接入。' },
      },
      {
        path: 'materials',
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '资料上传', description: '资料上传与 RAG 索引将在 P1.5 接入。' },
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
        component: () => import('@/views/PlaceholderView.vue'),
        meta: { title: '课程审核', description: '课程与资料审核将在 P1.4 / P1.5 接入。' },
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
