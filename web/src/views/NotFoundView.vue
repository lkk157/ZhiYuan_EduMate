<script setup>
import BrandLogo from '@/components/BrandLogo.vue'
</script>

<template>
  <div class="not-found">
    <div class="not-found-card em-card">
      <BrandLogo />
      <div class="code">404</div>
      <h1>页面走丢了</h1>
      <p>你访问的页面不存在，或已被移动到新的位置。</p>
      <router-link to="/login">
        <el-button type="primary" size="large">返回登录</el-button>
      </router-link>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 50% 0%, #e8f2ff, transparent 55%),
    var(--em-bg);
}

.not-found-card {
  width: min(480px, 100%);
  padding: 40px;
  text-align: center;
}

.code {
  margin-top: 26px;
  color: var(--em-primary);
  font-size: 74px;
  font-weight: 800;
  letter-spacing: -0.06em;
  line-height: 1;
}

.not-found-card h1 {
  margin-top: 10px;
  font-size: 24px;
}

.not-found-card p {
  margin: 8px 0 26px;
  color: var(--em-text-secondary);
}
</style>
