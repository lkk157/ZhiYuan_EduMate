<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Message, User } from '@element-plus/icons-vue'

import BrandLogo from '@/components/BrandLogo.vue'
import { useAuthStore } from '@/stores/auth'
import { homePathForRole } from '@/utils/roles'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const mode = ref('login')
const formRef = ref()
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
})

const isRegister = computed(() => mode.value === 'register')
const heading = computed(() => (isRegister.value ? '创建学生账号' : '欢迎回来'))
const subheading = computed(() =>
  isRegister.value
    ? '注册后即可加入课程、使用 AI 学伴并建立个人知识库'
    : '登录后进入你的学习与教学工作空间',
)
const submitText = computed(() => (isRegister.value ? '注册并登录' : '登录'))

function confirmValidator(_rule, value, callback) {
  if (!value) {
    callback(new Error('请再次输入密码'))
  } else if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

function emailValidator(_rule, value, callback) {
  if (!value) {
    callback()
    return
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim())) {
    callback(new Error('请输入正确的邮箱地址'))
    return
  }
  callback()
}

const rules = computed(() => ({
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度为 3-32 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      min: isRegister.value ? 8 : 6,
      max: 64,
      message: isRegister.value ? '密码长度为 8-64 个字符' : '密码长度为 6-64 个字符',
      trigger: 'blur',
    },
  ],
  confirmPassword: isRegister.value
    ? [
        { required: true, message: '请再次输入密码', trigger: 'blur' },
        { validator: confirmValidator, trigger: 'blur' },
      ]
    : [],
  email: isRegister.value
    ? [{ validator: emailValidator, trigger: 'blur' }]
    : [],
}))

function switchMode(next) {
  if (mode.value === next) return
  mode.value = next
  form.password = ''
  form.confirmPassword = ''
  formRef.value?.clearValidate()
}

async function validateForm() {
  try {
    await formRef.value?.validate()
    return true
  } catch {
    return false
  }
}

async function onLogin() {
  try {
    const user = await auth.login({
      username: form.username.trim(),
      password: form.password,
    })
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    router.push(redirect || homePathForRole(user?.role))
  } catch (error) {
    ElMessage.error(error?.message || '登录失败，请稍后重试')
  }
}

async function onRegister() {
  try {
    const user = await auth.register({
      username: form.username.trim(),
      password: form.password,
      password_confirm: form.password,
      email: form.email.trim() || null,
    })
    ElMessage.success('注册成功，已为你登录')
    router.push(homePathForRole(user?.role || 'student'))
  } catch (error) {
    ElMessage.error(error?.message || '注册失败，请稍后重试')
  }
}

async function onSubmit() {
  const username = form.username.trim()

  // Defensive client-side gate: keep the UX consistent even if a
  // component-level validation quirk lets an invalid submit through.
  if (!username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    formRef.value?.validate().catch(() => {})
    return
  }
  if (username.length < 3 || username.length > 32) {
    ElMessage.warning('用户名长度为 3-32 个字符')
    return
  }
  if (isRegister.value) {
    if (form.password.length < 8) {
      ElMessage.warning('密码长度为 8-64 个字符')
      return
    }
    if (form.password !== form.confirmPassword) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
    if (
      form.email &&
      !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email.trim())
    ) {
      ElMessage.warning('请输入正确的邮箱地址')
      return
    }
  } else if (form.password.length < 6) {
    ElMessage.warning('密码长度为 6-64 个字符')
    return
  }

  if (!(await validateForm())) return

  if (isRegister.value) {
    await onRegister()
  } else {
    await onLogin()
  }
}
</script>

<template>
  <div class="login-card">
    <BrandLogo class="login-brand" />

    <div class="auth-switch" role="tablist">
      <button
        type="button"
        :class="{ active: mode === 'login' }"
        @click="switchMode('login')"
      >
        登录
      </button>
      <button
        type="button"
        :class="{ active: mode === 'register' }"
        @click="switchMode('register')"
      >
        注册
      </button>
    </div>

    <div class="login-heading">
      <span class="em-eyebrow">{{ isRegister ? 'CREATE ACCOUNT' : 'WELCOME BACK' }}</span>
      <h2>{{ heading }}</h2>
      <p>{{ subheading }}</p>
    </div>

    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      size="large"
      class="login-form"
      @submit.prevent="onSubmit"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="form.username"
          placeholder="3-32 个字符，登录时不区分大小写"
          autocomplete="username"
          :prefix-icon="User"
        />
      </el-form-item>

      <el-form-item v-if="isRegister" label="邮箱（选填）" prop="email">
        <el-input
          v-model="form.email"
          type="email"
          placeholder="用于找回账号，可选"
          autocomplete="email"
          :prefix-icon="Message"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          :placeholder="isRegister ? '至少 8 个字符' : '请输入密码'"
          :autocomplete="isRegister ? 'new-password' : 'current-password'"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <el-form-item v-if="isRegister" label="确认密码" prop="confirmPassword">
        <el-input
          v-model="form.confirmPassword"
          type="password"
          show-password
          placeholder="请再次输入密码"
          autocomplete="new-password"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <div class="login-options">
        <el-checkbox v-if="!isRegister">记住登录状态</el-checkbox>
        <span v-else class="register-note">注册后默认为学生角色</span>
        <button v-if="!isRegister" class="link-button" type="button">忘记密码？</button>
      </div>

      <el-button
        type="primary"
        size="large"
        native-type="submit"
        class="login-submit"
        :loading="auth.loading"
      >
        {{ submitText }}
      </el-button>
    </el-form>

    <div class="login-hint">
      <el-icon><InfoFilled /></el-icon>
      <span v-if="isRegister">
        学生可自助注册；注册后可通过邀请码或教师添加加入课程，并建立自己的知识库。
      </span>
      <span v-else>
        学生可自助注册；教师与管理员账号由管理员统一创建和分配。
      </span>
    </div>

    <div class="login-roles">
      <span><i class="dot dot-student" />学生端</span>
      <span><i class="dot dot-teacher" />教师端</span>
      <span><i class="dot dot-admin" />管理员端</span>
    </div>
  </div>
</template>

<style scoped>
.login-card {
  width: 100%;
  max-width: 420px;
}

.login-brand {
  margin-bottom: 26px;
}

.auth-switch {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: #f1f6fd;
}

.auth-switch button {
  min-width: 78px;
  padding: 8px 18px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #62738a;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
}

.auth-switch button.active {
  background: #fff;
  color: var(--em-primary);
  box-shadow: 0 4px 12px rgba(22, 119, 255, 0.16);
}

.login-heading {
  margin-top: 22px;
}

.login-heading h2 {
  margin-top: 8px;
  font-size: 30px;
  font-weight: 750;
  letter-spacing: -0.03em;
}

.login-heading p {
  margin-top: 8px;
  color: var(--em-text-secondary);
}

.login-form {
  margin-top: 24px;
}

.login-form :deep(.el-form-item__label) {
  color: #40526a;
  font-weight: 600;
}

.login-form :deep(.el-input__wrapper) {
  height: 48px;
  border-radius: 12px;
  background: #fbfdff;
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2px 0 20px;
}

.register-note {
  color: var(--em-text-muted);
  font-size: 12px;
}

.link-button {
  border: 0;
  background: transparent;
  color: var(--em-primary);
  cursor: pointer;
  font-size: 13px;
}

.login-submit {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.04em;
  box-shadow: 0 12px 24px rgba(22, 119, 255, 0.22);
}

.login-hint {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-top: 22px;
  padding: 12px 14px;
  border-radius: 12px;
  background: var(--em-primary-softer);
  color: #5b6f88;
  font-size: 12px;
  line-height: 1.6;
}

.login-hint .el-icon {
  margin-top: 3px;
  color: var(--em-primary);
  flex: 0 0 auto;
}

.login-roles {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 22px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.login-roles span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot-student {
  background: #1677ff;
}

.dot-teacher {
  background: #22c55e;
}

.dot-admin {
  background: #f59e0b;
}
</style>
