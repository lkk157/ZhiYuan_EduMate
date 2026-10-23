import { defineStore } from 'pinia'

import {
  fetchMe,
  login as loginApi,
  register as registerApi,
} from '@/api/auth'
import { TOKEN_KEY, USER_KEY } from '@/api/http'

function readStoredUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) || '',
    user: readStoredUser(),
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.token),
    role: (state) => state.user?.role || '',
    displayName: (state) => state.user?.username || '未登录',
    initial: (state) => (state.user?.username || 'E').slice(0, 1).toUpperCase(),
  },

  actions: {
    persist() {
      if (this.token) {
        localStorage.setItem(TOKEN_KEY, this.token)
      } else {
        localStorage.removeItem(TOKEN_KEY)
      }

      if (this.user) {
        localStorage.setItem(USER_KEY, JSON.stringify(this.user))
      } else {
        localStorage.removeItem(USER_KEY)
      }
    },

    applyAuthPayload(body) {
      const data = body?.data || {}
      this.token = data.access_token || ''
      this.user = data.user || null
      this.persist()
      return this.user
    },

    async login(credentials) {
      this.loading = true
      try {
        const body = await loginApi(credentials)
        return this.applyAuthPayload(body)
      } finally {
        this.loading = false
      }
    },

    async register(payload) {
      this.loading = true
      try {
        const body = await registerApi(payload)
        return this.applyAuthPayload(body)
      } finally {
        this.loading = false
      }
    },

    async refreshUser() {
      const body = await fetchMe()
      this.user = body?.data || null
      this.persist()
      return this.user
    },

    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
    },
  },
})
