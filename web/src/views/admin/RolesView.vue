<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Key, Lock, User } from '@element-plus/icons-vue'

import { fetchRoleOverview } from '@/api/admin'
import { roleLabel } from '@/utils/roles'

const loading = ref(false)
const roles = ref([])
const permissions = ref([])

const roleTagTypes = { admin: 'danger', teacher: 'success', student: 'primary' }
const roleOrder = ['admin', 'teacher', 'student']
const orderedRoles = computed(() =>
  [...roles.value].sort(
    (a, b) => roleOrder.indexOf(a.name) - roleOrder.indexOf(b.name),
  ),
)
const totalGrants = computed(() =>
  roles.value.reduce((sum, role) => sum + role.permissions.length, 0),
)

async function load() {
  loading.value = true
  try {
    const body = await fetchRoleOverview()
    roles.value = body?.data?.roles || []
    permissions.value = body?.data?.permissions || []
  } catch (error) {
    ElMessage.error(error?.message || '加载角色权限失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="em-page roles-page" v-loading="loading">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">ROLE MATRIX</span>
        <h1>角色权限</h1>
        <p>查看系统内置角色的权限矩阵。细粒度权限编辑将在阶段二提供。</p>
      </div>
      <div class="summary-chip">
        <el-icon><Lock /></el-icon>
        <span>{{ roles.length }} 个角色 · {{ permissions.length }} 项权限 · {{ totalGrants }} 项授权</span>
      </div>
    </div>

    <section class="role-grid">
      <article v-for="role in orderedRoles" :key="role.name" class="role-card em-card">
        <div class="role-head">
          <div class="role-icon" :class="`role-${role.name}`">
            <el-icon><component :is="role.name === 'student' ? User : Key" /></el-icon>
          </div>
          <el-tag :type="roleTagTypes[role.name] || 'info'" effect="light">
            {{ roleLabel(role.name) }}
          </el-tag>
        </div>
        <h3>{{ roleLabel(role.name) }}端</h3>
        <p>{{ role.description || '暂无角色说明' }}</p>
        <div class="role-stats">
          <span><strong>{{ role.user_count }}</strong> 个账号</span>
          <span><strong>{{ role.permissions.length }}</strong> 项权限</span>
        </div>
      </article>
    </section>

    <section class="matrix-card em-card">
      <div class="matrix-head">
        <div>
          <span class="em-eyebrow">PERMISSION MATRIX</span>
          <h2>权限矩阵</h2>
        </div>
        <span class="matrix-note">只读视图</span>
      </div>

      <el-table :data="permissions" class="matrix-table">
        <el-table-column label="权限" min-width="240">
          <template #default="{ row }">
            <div class="permission-cell">
              <strong>{{ row.name }}</strong>
              <small>{{ row.code }}</small>
              <span>{{ row.description }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column
          v-for="role in orderedRoles"
          :key="role.name"
          :label="roleLabel(role.name)"
          width="140"
          align="center"
        >
          <template #default="{ row }">
            <el-icon
              v-if="role.permissions.includes(row.code)"
              class="perm-yes"
              aria-label="已授权"
            >
              <CircleCheckFilled />
            </el-icon>
            <span v-else class="perm-no">—</span>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty description="暂无权限数据" :image-size="80" />
        </template>
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.roles-page {
  display: grid;
  gap: 18px;
}

.summary-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border: 1px solid var(--em-border);
  border-radius: 999px;
  background: #fff;
  color: var(--em-text-secondary);
  font-size: 12px;
  box-shadow: var(--em-shadow-card);
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.role-card {
  padding: 22px 24px;
}

.role-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.role-icon {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  border-radius: 13px;
  font-size: 20px;
}

.role-admin {
  background: #fff1e8;
  color: #ea580c;
}

.role-teacher {
  background: #e9fbf1;
  color: #16a34a;
}

.role-student {
  background: var(--em-primary-soft);
  color: var(--em-primary);
}

.role-card h3 {
  margin-top: 16px;
  font-size: 17px;
}

.role-card p {
  min-height: 42px;
  margin-top: 6px;
  color: var(--em-text-secondary);
  font-size: 12px;
}

.role-stats {
  display: flex;
  gap: 18px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--em-border);
  color: var(--em-text-muted);
  font-size: 12px;
}

.role-stats strong {
  color: var(--em-text);
  font-size: 16px;
}

.matrix-card {
  padding: 22px 24px 12px;
}

.matrix-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.matrix-head h2 {
  margin-top: 4px;
  font-size: 19px;
}

.matrix-note {
  padding: 5px 12px;
  border-radius: 999px;
  background: #f4f7fc;
  color: var(--em-text-muted);
  font-size: 12px;
}

.permission-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
}

.permission-cell strong {
  font-size: 14px;
}

.permission-cell small {
  color: var(--em-primary);
  font-family: "JetBrains Mono", Consolas, monospace;
  font-size: 11px;
}

.permission-cell span {
  margin-top: 2px;
  color: var(--em-text-muted);
  font-size: 12px;
}

.perm-yes {
  color: #16a34a;
  font-size: 19px;
}

.perm-no {
  color: #cbd7e6;
}

@media (max-width: 1024px) {
  .role-grid {
    grid-template-columns: 1fr;
  }
}
</style>
