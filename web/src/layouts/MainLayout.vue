<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowDown, Bell, Expand, Fold, Search } from '@element-plus/icons-vue'

import BrandLogo from '@/components/BrandLogo.vue'
import { useAuthStore } from '@/stores/auth'
import { menuForRole, roleLabel } from '@/utils/roles'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const search = ref('')
const collapsed = ref(false)
const mobileOpen = ref(false)

const role = computed(() => {
  if (auth.role) return auth.role
  const matched = route.matched.find((record) => record.meta?.role)
  return matched?.meta?.role || 'student'
})

const menus = computed(() => menuForRole(role.value))
const pageTitle = computed(() => route.meta?.title || '工作台')
const roleName = computed(() => roleLabel(role.value))
const displayName = computed(() => auth.displayName)
const initial = computed(() => auth.initial)

function toggleSidebar() {
  if (window.innerWidth < 1024) {
    mobileOpen.value = !mobileOpen.value
  } else {
    collapsed.value = !collapsed.value
  }
}

function closeMobile() {
  mobileOpen.value = false
}

function onCommand(command) {
  if (command === 'logout') {
    auth.logout()
    router.push('/login')
  }
}
</script>

<template>
  <div
    class="app-shell"
    :class="{ 'is-collapsed': collapsed, 'is-mobile-open': mobileOpen }"
  >
    <div v-if="mobileOpen" class="mobile-mask" @click="closeMobile" />

    <aside class="sidebar">
      <div class="sidebar-brand">
        <BrandLogo :compact="collapsed" />
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in menus"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          active-class="is-active"
          @click="closeMobile"
        >
          <el-icon class="nav-icon">
            <component :is="item.icon" />
          </el-icon>
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="sidebar-role">
          <div class="role-avatar">{{ initial }}</div>
          <div v-if="!collapsed" class="role-meta">
            <strong>{{ displayName }}</strong>
            <span>{{ roleName }}端</span>
          </div>
        </div>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <button class="icon-button" type="button" aria-label="切换侧栏" @click="toggleSidebar">
            <el-icon>
              <component :is="collapsed ? Expand : Fold" />
            </el-icon>
          </button>
          <div class="topbar-title">
            <span class="em-eyebrow">{{ roleName }}空间</span>
            <h2>{{ pageTitle }}</h2>
          </div>
        </div>

        <div class="topbar-right">
          <el-input
            v-model="search"
            class="topbar-search"
            placeholder="搜索课程、资料…"
            :prefix-icon="Search"
            clearable
          />
          <button class="icon-button" type="button" aria-label="通知">
            <el-badge is-dot>
              <el-icon><Bell /></el-icon>
            </el-badge>
          </button>

          <el-dropdown trigger="click" @command="onCommand">
            <button class="user-chip" type="button">
              <div class="user-avatar">{{ initial }}</div>
              <div class="user-meta">
                <strong>{{ displayName }}</strong>
                <span>{{ roleName }}</span>
              </div>
              <el-icon class="user-arrow"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="page-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  min-height: 100vh;
  background: var(--em-bg);
}

.sidebar {
  position: sticky;
  top: 0;
  display: flex;
  width: var(--em-sidebar-width);
  height: 100vh;
  flex: 0 0 var(--em-sidebar-width);
  flex-direction: column;
  padding: 22px 16px 18px;
  border-right: 1px solid var(--em-border);
  background: #fff;
  transition: width 0.2s ease, flex-basis 0.2s ease, transform 0.2s ease;
  z-index: 20;
}

.is-collapsed .sidebar {
  width: 84px;
  flex-basis: 84px;
  padding-inline: 12px;
}

.sidebar-brand {
  padding: 4px 6px 22px;
}

.sidebar-nav {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: 12px;
  color: #52637a;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.15s ease, color 0.15s ease;
}

.nav-item:hover {
  background: var(--em-primary-softer);
  color: var(--em-primary);
}

.nav-item.is-active {
  background: linear-gradient(135deg, var(--em-primary), #3d8bff);
  color: #fff;
  box-shadow: 0 10px 22px rgba(22, 119, 255, 0.24);
}

.nav-icon {
  font-size: 18px;
}

.is-collapsed .nav-item {
  justify-content: center;
  padding: 0;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid var(--em-border);
}

.sidebar-role {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 12px;
  background: #f8faff;
}

.role-avatar,
.user-avatar {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: linear-gradient(135deg, #1677ff, #74b4ff);
  color: #fff;
  font-weight: 700;
}

.role-meta,
.user-meta {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.25;
}

.role-meta strong,
.user-meta strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.role-meta span,
.user-meta span {
  color: var(--em-text-muted);
  font-size: 11px;
}

.main-area {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  min-height: 74px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 28px;
  border-bottom: 1px solid rgba(232, 238, 247, 0.8);
  background: rgba(245, 247, 251, 0.88);
  backdrop-filter: blur(14px);
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 14px;
}

.topbar-title h2 {
  font-size: 19px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.icon-button,
.user-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--em-border);
  background: #fff;
  color: #53657d;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease;
}

.icon-button {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  font-size: 17px;
}

.icon-button:hover {
  border-color: #b9d4ff;
  color: var(--em-primary);
}

.topbar-search {
  width: 230px;
}

.topbar-search :deep(.el-input__wrapper) {
  height: 38px;
  border-radius: 11px;
  background: #fff;
}

.user-chip {
  gap: 10px;
  padding: 4px 10px 4px 4px;
  border-radius: 999px;
}

.user-chip:hover {
  border-color: #b9d4ff;
}

.user-meta {
  align-items: flex-start;
  text-align: left;
}

.user-arrow {
  color: var(--em-text-muted);
  font-size: 12px;
}

.page-content {
  width: 100%;
  flex: 1;
  padding: 26px 28px 40px;
}

.mobile-mask {
  position: fixed;
  inset: 0;
  z-index: 15;
  background: rgba(20, 35, 55, 0.36);
}

@media (max-width: 1180px) {
  .topbar-search {
    width: 180px;
  }
}

@media (max-width: 1023px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    transform: translateX(-100%);
  }

  .is-mobile-open .sidebar {
    transform: translateX(0);
  }

  .is-collapsed .sidebar {
    width: var(--em-sidebar-width);
    flex-basis: var(--em-sidebar-width);
  }

  .topbar-search {
    display: none;
  }

  .topbar {
    padding-inline: 18px;
  }

  .page-content {
    padding: 20px 18px 32px;
  }
}

@media (max-width: 640px) {
  .user-meta,
  .user-arrow {
    display: none;
  }

  .user-chip {
    padding: 4px;
  }
}
</style>
