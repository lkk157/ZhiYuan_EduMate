<script setup>
import { onMounted, ref } from 'vue'

import { getReadiness } from '@/api/health'

const readiness = ref(null)
const readinessError = ref('')

const stats = [
  { label: '用户总数', value: '—', hint: 'P1.3 接入', icon: 'User', tone: 'blue' },
  { label: '待审核课程', value: '—', hint: 'P1.4 接入', icon: 'Document', tone: 'orange' },
  { label: '待审核资料', value: '—', hint: 'P1.5 接入', icon: 'Files', tone: 'green' },
  { label: '今日操作', value: '—', hint: 'P1.3 接入', icon: 'Tickets', tone: 'purple' },
]

const shortcuts = [
  { title: '用户管理', text: '账号、角色与状态', path: '/admin/users', icon: 'User' },
  { title: '课程审核', text: '课程与资料审核', path: '/admin/reviews', icon: 'DocumentChecked' },
  { title: '审计日志', text: '关键操作可追溯', path: '/admin/audit', icon: 'Tickets' },
  { title: '系统配置', text: 'RAG 与推荐策略', path: '/admin/settings', icon: 'Setting' },
]

const checkLabels = {
  database: '数据库',
  redis: 'Redis 缓存',
}

onMounted(async () => {
  try {
    const body = await getReadiness()
    readiness.value = body?.data || null
  } catch (error) {
    readinessError.value = error?.message || '无法获取服务状态'
  }
})
</script>

<template>
  <div class="em-page admin-home">
    <section class="hero em-card">
      <div>
        <span class="em-eyebrow">ADMIN CONSOLE</span>
        <h1>系统治理中心</h1>
        <p>用户、权限、审核、审计与系统配置的统一入口。</p>
      </div>
      <div class="hero-status">
        <span class="status-dot" :class="{ ok: readiness?.status === 'ok' }" />
        <div>
          <strong>{{ readiness?.status === 'ok' ? '服务运行正常' : '状态待确认' }}</strong>
          <small v-if="readiness">版本 {{ readiness.version }}</small>
          <small v-else-if="readinessError">{{ readinessError }}</small>
          <small v-else>正在检查…</small>
        </div>
      </div>
    </section>

    <section class="stat-grid">
      <article v-for="item in stats" :key="item.label" class="stat-card em-card">
        <div class="stat-icon" :class="`tone-${item.tone}`">
          <el-icon><component :is="item.icon" /></el-icon>
        </div>
        <div class="stat-body">
          <span>{{ item.label }}</span>
          <strong>{{ item.value }}</strong>
          <small>{{ item.hint }}</small>
        </div>
      </article>
    </section>

    <section class="content-grid">
      <div class="shortcut-card em-card">
        <div class="section-head">
          <div>
            <span class="em-eyebrow">SHORTCUTS</span>
            <h2>快捷入口</h2>
          </div>
        </div>
        <div class="shortcut-grid">
          <router-link v-for="item in shortcuts" :key="item.title" :to="item.path" class="shortcut">
            <el-icon><component :is="item.icon" /></el-icon>
            <div>
              <strong>{{ item.title }}</strong>
              <small>{{ item.text }}</small>
            </div>
          </router-link>
        </div>
      </div>

      <div class="health-card em-card">
        <div class="section-head">
          <div>
            <span class="em-eyebrow">SYSTEM HEALTH</span>
            <h2>服务状态</h2>
          </div>
          <el-tag v-if="readiness" round :type="readiness.status === 'ok' ? 'success' : 'warning'">
            {{ readiness.status }}
          </el-tag>
        </div>

        <div v-if="readiness" class="health-list">
          <div v-for="(value, key) in readiness.checks" :key="key" class="health-row">
            <span>{{ checkLabels[key] || key }}</span>
            <span class="health-value" :class="value">{{ value }}</span>
          </div>
          <div class="health-row">
            <span>RAG 服务</span>
            <span class="health-value muted">P1.5 接入</span>
          </div>
        </div>

        <el-empty v-else-if="readinessError" :description="readinessError" :image-size="80" />
        <div v-else class="health-loading">正在检查数据库与缓存…</div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.admin-home {
  display: grid;
  gap: 22px;
}

.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  padding: 32px 36px;
  background:
    radial-gradient(circle at 92% 10%, rgba(245, 158, 11, 0.1), transparent 34%),
    linear-gradient(135deg, #ffffff, #fffaf1);
}

.hero h1 {
  margin-top: 8px;
  font-size: 32px;
  font-weight: 760;
  letter-spacing: -0.035em;
}

.hero p {
  margin-top: 8px;
  color: var(--em-text-secondary);
}

.hero-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border: 1px solid var(--em-border);
  border-radius: 14px;
  background: #fff;
  box-shadow: var(--em-shadow-card);
}

.hero-status div {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.hero-status strong {
  font-size: 13px;
}

.hero-status small {
  color: var(--em-text-muted);
  font-size: 11px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 0 5px rgba(245, 158, 11, 0.14);
}

.status-dot.ok {
  background: #22c55e;
  box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.14);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px;
}

.stat-icon {
  display: grid;
  width: 48px;
  height: 48px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 14px;
  font-size: 22px;
}

.tone-blue { background: #e8f2ff; color: #1677ff; }
.tone-orange { background: #fff5e6; color: #ea8a0a; }
.tone-green { background: #e9fbf1; color: #16a34a; }
.tone-purple { background: #f1ecff; color: #7c5cff; }

.stat-body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.3;
}

.stat-body span { color: var(--em-text-secondary); font-size: 12px; }
.stat-body strong { margin-top: 2px; font-size: 24px; font-weight: 750; }
.stat-body small { color: var(--em-text-muted); font-size: 11px; }

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(0, 0.7fr);
  gap: 18px;
}

.shortcut-card,
.health-card {
  padding: 24px 26px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.section-head h2 {
  margin-top: 4px;
  font-size: 19px;
}

.shortcut-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.shortcut {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--em-border);
  border-radius: 14px;
  background: #fbfdff;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.shortcut:hover {
  border-color: #b9d4ff;
  transform: translateY(-1px);
}

.shortcut .el-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 12px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 19px;
}

.shortcut div {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.shortcut strong {
  font-size: 14px;
}

.shortcut small {
  color: var(--em-text-muted);
  font-size: 11px;
}

.health-list {
  display: grid;
  gap: 10px;
  margin-top: 18px;
}

.health-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 14px;
  border-radius: 11px;
  background: #f8faff;
  color: #52637a;
}

.health-value {
  font-weight: 600;
  text-transform: uppercase;
  font-size: 11px;
  letter-spacing: 0.06em;
}

.health-value.ok { color: #16a34a; }
.health-value.error { color: #ef4444; }
.health-value.disabled,
.health-value.muted { color: #98a6b8; }

.health-loading {
  margin-top: 18px;
  padding: 24px;
  border-radius: 12px;
  background: #f8faff;
  color: var(--em-text-secondary);
  text-align: center;
}

@media (max-width: 1180px) {
  .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .content-grid { grid-template-columns: 1fr; }
}

@media (max-width: 760px) {
  .hero { flex-direction: column; align-items: flex-start; }
  .stat-grid { grid-template-columns: 1fr; }
  .shortcut-grid { grid-template-columns: 1fr; }
}
</style>
