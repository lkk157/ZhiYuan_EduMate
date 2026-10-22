<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '该模块正在建设中。' },
  phase: { type: String, default: '阶段一' },
  items: { type: Array, default: () => [] },
})
</script>

<template>
  <div class="em-page">
    <div class="em-page-header">
      <div>
        <span class="em-eyebrow">MODULE PREVIEW</span>
        <h1>{{ title }}</h1>
        <p>{{ description }}</p>
      </div>
      <el-tag round effect="light" type="primary">{{ phase }}</el-tag>
    </div>

    <div class="placeholder-card em-card">
      <div class="placeholder-icon">
        <el-icon><Tools /></el-icon>
      </div>
      <h3>功能正在接入</h3>
      <p>页面骨架与导航已就绪，业务接口将在对应阶段完成后自动启用。</p>

      <ul v-if="items.length" class="placeholder-list">
        <li v-for="item in items" :key="item">
          <el-icon><CircleCheck /></el-icon>
          <span>{{ item }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.placeholder-card {
  display: flex;
  min-height: 380px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 28px;
  text-align: center;
}

.placeholder-icon {
  display: grid;
  width: 68px;
  height: 68px;
  place-items: center;
  border-radius: 22px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 28px;
}

.placeholder-card h3 {
  margin-top: 18px;
  font-size: 19px;
}

.placeholder-card > p {
  max-width: 460px;
  margin-top: 8px;
  color: var(--em-text-secondary);
}

.placeholder-list {
  display: grid;
  gap: 10px;
  margin: 24px 0 0;
  padding: 0;
  list-style: none;
  color: #52637a;
  text-align: left;
}

.placeholder-list li {
  display: flex;
  align-items: center;
  gap: 8px;
}

.placeholder-list .el-icon {
  color: var(--em-primary);
}
</style>
