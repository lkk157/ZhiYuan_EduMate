<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'

import {
  createUser,
  listUsers,
  resetUserPassword,
  setUserStatus,
  updateUser,
} from '@/api/admin'
import { useAuthStore } from '@/stores/auth'
import { formatDateTime } from '@/utils/format'
import { ROLE_LABELS, roleLabel } from '@/utils/roles'

const auth = useAuthStore()

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const filters = reactive({ keyword: '', role: '', status: '' })

const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }))
const statusOptions = [
  { value: 'active', label: '启用' },
  { value: 'disabled', label: '禁用' },
]
const roleTagTypes = { admin: 'danger', teacher: 'success', student: 'primary' }

const createVisible = ref(false)
const createFormRef = ref()
const creating = ref(false)
const createForm = reactive({
  username: '',
  email: '',
  password: '',
  role: 'student',
})

const editVisible = ref(false)
const editFormRef = ref()
const savingEdit = ref(false)
const editing = ref(null)
const editForm = reactive({ email: '', role: 'student' })

const resetVisible = ref(false)
const resetFormRef = ref()
const resetting = ref(false)
const resetTarget = ref(null)
const resetForm = reactive({ password: '', confirmPassword: '' })

function optionalEmail(_rule, value, callback) {
  if (!value || !value.trim()) {
    callback()
    return
  }
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim())) {
    callback(new Error('请输入正确的邮箱地址'))
    return
  }
  callback()
}

function confirmPasswordValidator(_rule, value, callback) {
  if (!value) {
    callback(new Error('请再次输入新密码'))
  } else if (value !== resetForm.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const createRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '用户名长度为 3-32 个字符', trigger: 'blur' },
  ],
  email: [{ validator: optionalEmail, trigger: 'blur' }],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8-64 个字符', trigger: 'blur' },
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const editRules = {
  email: [{ validator: optionalEmail, trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

const resetRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, max: 64, message: '密码长度为 8-64 个字符', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: confirmPasswordValidator, trigger: 'blur' },
  ],
}

async function load() {
  loading.value = true
  try {
    const body = await listUsers({
      page: page.value,
      page_size: pageSize.value,
      keyword: filters.keyword.trim() || undefined,
      role: filters.role || undefined,
      status: filters.status || undefined,
    })
    items.value = body?.data?.items || []
    total.value = body?.data?.total || 0
  } catch (error) {
    ElMessage.error(error?.message || '加载用户列表失败')
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

function resetFilters() {
  filters.keyword = ''
  filters.role = ''
  filters.status = ''
  search()
}

function onSizeChange() {
  page.value = 1
  load()
}

function openCreate() {
  Object.assign(createForm, { username: '', email: '', password: '', role: 'student' })
  createVisible.value = true
}

async function submitCreate() {
  try {
    await createFormRef.value?.validate()
  } catch {
    return
  }
  creating.value = true
  try {
    await createUser({
      username: createForm.username.trim(),
      email: createForm.email.trim() || null,
      password: createForm.password,
      role: createForm.role,
    })
    ElMessage.success('用户创建成功')
    createVisible.value = false
    page.value = 1
    await load()
  } catch (error) {
    ElMessage.error(error?.message || '创建用户失败')
  } finally {
    creating.value = false
  }
}

function openEdit(row) {
  editing.value = row
  editForm.email = row.email || ''
  editForm.role = row.role
  editVisible.value = true
}

async function submitEdit() {
  try {
    await editFormRef.value?.validate()
  } catch {
    return
  }
  savingEdit.value = true
  try {
    await updateUser(editing.value.id, {
      email: editForm.email.trim() || '',
      role: editForm.role,
    })
    ElMessage.success('用户信息已更新')
    editVisible.value = false
    await load()
  } catch (error) {
    ElMessage.error(error?.message || '更新用户失败')
  } finally {
    savingEdit.value = false
  }
}

function openReset(row) {
  resetTarget.value = row
  resetForm.password = ''
  resetForm.confirmPassword = ''
  resetVisible.value = true
}

async function submitReset() {
  try {
    await resetFormRef.value?.validate()
  } catch {
    return
  }
  resetting.value = true
  try {
    await resetUserPassword(resetTarget.value.id, resetForm.password)
    ElMessage.success('密码已重置，请通知用户使用新密码登录')
    resetVisible.value = false
  } catch (error) {
    ElMessage.error(error?.message || '重置密码失败')
  } finally {
    resetting.value = false
  }
}

async function toggleStatus(row) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  const label = next === 'disabled' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定要${label}用户「${row.username}」吗？${
        next === 'disabled' ? '禁用后该用户将立即退出登录。' : ''
      }`,
      `${label}账号`,
      {
        type: next === 'disabled' ? 'warning' : 'info',
        confirmButtonText: label,
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  try {
    await setUserStatus(row.id, next)
    ElMessage.success(`已${label}用户「${row.username}」`)
    await load()
  } catch (error) {
    ElMessage.error(error?.message || `${label}用户失败`)
  }
}

onMounted(load)
</script>

<template>
  <div class="em-page users-page">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">USER GOVERNANCE</span>
        <h1>用户管理</h1>
        <p>创建教师与管理员账号、分配角色、启禁用账号、重置密码。</p>
      </div>
      <el-button type="primary" size="large" :icon="Plus" @click="openCreate">
        创建用户
      </el-button>
    </div>

    <section class="filter-card em-card">
      <div class="filter-row">
        <el-input
          v-model="filters.keyword"
          class="keyword-input"
          placeholder="搜索用户名或邮箱"
          :prefix-icon="Search"
          clearable
          @keyup.enter="search"
          @clear="search"
        />
        <el-select v-model="filters.role" placeholder="全部角色" clearable class="filter-select">
          <el-option
            v-for="item in roleOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-select
          v-model="filters.status"
          placeholder="全部状态"
          clearable
          class="filter-select"
        >
          <el-option
            v-for="item in statusOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-button type="primary" :icon="Search" @click="search">查询</el-button>
        <el-button :icon="Refresh" @click="resetFilters">重置</el-button>
      </div>
    </section>

    <section class="table-card em-card">
      <el-table v-loading="loading" :data="items" class="user-table">
        <el-table-column label="用户" min-width="230">
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar">{{ row.username.slice(0, 1).toUpperCase() }}</div>
              <div class="user-identity">
                <strong>{{ row.username }}</strong>
                <small>{{ row.email || '未设置邮箱' }}</small>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色" width="110">
          <template #default="{ row }">
            <el-tag :type="roleTagTypes[row.role] || 'info'" effect="light">
              {{ roleLabel(row.role) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" effect="plain">
              {{ row.status === 'active' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="最近登录" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.last_login_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDateTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="primary" @click="openReset(row)">重置密码</el-button>
              <el-button
                link
                :type="row.status === 'active' ? 'danger' : 'success'"
                :disabled="row.status === 'active' && row.id === auth.user?.id"
                :title="row.id === auth.user?.id ? '不能禁用自己的账号' : ''"
                @click="toggleStatus(row)"
              >
                {{ row.status === 'active' ? '禁用' : '启用' }}
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="没有匹配的用户" :image-size="80" />
        </template>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @current-change="load"
          @size-change="onSizeChange"
        />
      </div>
    </section>

    <el-dialog v-model="createVisible" title="创建用户" width="520px">
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-position="top"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="createForm.username"
            placeholder="3-32 个字符，登录时不区分大小写"
          />
        </el-form-item>
        <el-form-item label="邮箱（选填）" prop="email">
          <el-input v-model="createForm.email" placeholder="用于账号联系，可选" />
        </el-form-item>
        <el-form-item label="初始密码" prop="password">
          <el-input
            v-model="createForm.password"
            type="password"
            show-password
            placeholder="至少 8 个字符"
          />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="createForm.role" class="full-width">
            <el-option
              v-for="item in roleOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">
          创建
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑用户" width="520px">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-position="top">
        <el-form-item label="用户名">
          <el-input :model-value="editing?.username" disabled />
        </el-form-item>
        <el-form-item label="邮箱（选填）" prop="email">
          <el-input v-model="editForm.email" placeholder="留空表示不设置邮箱" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" class="full-width">
            <el-option
              v-for="item in roleOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <p class="dialog-hint">修改角色会立即使该用户当前的登录令牌失效。</p>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="submitEdit">
          保存
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resetVisible" title="重置密码" width="480px">
      <p class="dialog-lead">
        为用户 <strong>{{ resetTarget?.username }}</strong> 设置新密码，保存后旧密码与旧令牌立即失效。
      </p>
      <el-form
        ref="resetFormRef"
        :model="resetForm"
        :rules="resetRules"
        label-position="top"
      >
        <el-form-item label="新密码" prop="password">
          <el-input
            v-model="resetForm.password"
            type="password"
            show-password
            placeholder="至少 8 个字符"
          />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="resetForm.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="resetting" @click="submitReset">
          确认重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.users-page {
  display: grid;
  gap: 18px;
}

.filter-card {
  padding: 18px 20px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.keyword-input {
  width: 240px;
}

.filter-select {
  width: 140px;
}

.table-card {
  padding: 8px 8px 18px;
  overflow: hidden;
}

.user-table {
  width: 100%;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #e8f2ff, #d7e8ff);
  color: var(--em-primary);
  font-weight: 700;
}

.user-identity {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.35;
}

.user-identity strong {
  font-size: 14px;
}

.user-identity small {
  color: var(--em-text-muted);
  font-size: 12px;
}

.time-text {
  color: var(--em-text-secondary);
  font-size: 12px;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  padding: 14px 14px 0;
}

.full-width {
  width: 100%;
}

.dialog-lead {
  margin-bottom: 18px;
  color: var(--em-text-secondary);
}

.dialog-hint {
  color: var(--em-text-muted);
  font-size: 12px;
}

@media (max-width: 760px) {
  .keyword-input,
  .filter-select {
    width: 100%;
  }

  .filter-row :deep(.el-button) {
    flex: 1;
  }
}
</style>
