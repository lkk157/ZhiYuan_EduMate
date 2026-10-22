import axios from 'axios'

const TOKEN_KEY = 'edumate_token'
const USER_KEY = 'edumate_user'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 310000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const body = error.response?.data
    const message = body?.message || error.message || '网络请求失败'

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      if (!window.location.pathname.startsWith('/login')) {
        window.location.assign('/login')
      }
    }

    const normalized = new Error(message)
    normalized.status = status
    normalized.code = body?.code
    normalized.payload = body?.data
    return Promise.reject(normalized)
  },
)

export { TOKEN_KEY, USER_KEY }
export default http
