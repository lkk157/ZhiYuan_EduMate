<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'

import BrandLogo from '@/components/BrandLogo.vue'
import { useAuthStore } from '@/stores/auth'
import { homePathForRole } from '@/utils/roles'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const formRef = ref()
const form = reactive({ username: '', password: '' })
const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度为 3-32 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度为 6-64 个字符', trigger: 'blur' },
  ],
}

async function onSubmit() {
  const username = form.username.trim()

  // Defensive client-side gate: never call the API with empty credentials,
  // even if a component-level validation quirk lets the submit through.
  if (!username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    formRef.value?.validate().catch(() => {})
    return
  }
  if (username.length < 3 || username.length > 32) {
    ElMessage.warning('用户名长度为 3-32 个字符')
    return
  }
  if (form.password.length < 6 || form.password.length > 64) {
    ElMessage.warning('密码长度为 6-64 个字符')
    return
  }

  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  try {
    const user = await auth.login({ username: form.username, password: form.password })
    ElMessage.success('登录成功')
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : ''
    router.push(redirect || homePathForRole(user?.role))
  } catch (error) {
    ElMessage.error(error?.message || '登录失败，请稍后重试')
  }
}
</script>

<template>
  <div class="login-card">
    <BrandLogo class="login-brand" />

    <div class="login-heading">
      <span class="em-eyebrow">WELCOME BACK</span>
      <h2>欢迎回来</h2>
      <p>登录后进入你的学习与教学工作空间</p>
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
          placeholder="请输入用户名"
          autocomplete="username"
          :prefix-icon="User"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="请输入密码"
          autocomplete="current-password"
          :prefix-icon="Lock"
        />
      </el-form-item>

      <div class="login-options">
        <el-checkbox>记住登录状态</el-checkbox>
        <button class="link-button" type="button">忘记密码？</button>
      </div>

      <el-button
        type="primary"
        size="large"
        native-type="submit"
        class="login-submit"
        :loading="auth.loading"
      >
        登录
      </el-button>
    </el-form>

    <div class="login-hint">
      <el-icon><InfoFilled /></el-icon>
      <span>账号由管理员统一分配。学生、教师、管理员登录后自动进入对应空间。</span>
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
  margin-bottom: 34px;
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
  margin-top: 28px;
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
  margin-top: 26px;
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
