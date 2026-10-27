<script setup>
import BrandLogo from '@/components/BrandLogo.vue'

const features = [
  { title: '课程知识库问答', text: '基于课程资料检索与生成，答案附引用来源' },
  { title: '个性化学习推荐', text: '结合掌握度推荐资料、习题与学习路径' },
  { title: '教师学情看板', text: '薄弱知识点、高频问题与班级掌握度一屏掌握' },
]
</script>

<template>
  <div class="auth-shell">
    <section class="auth-brand">
      <div class="orb orb-a" />
      <div class="orb orb-b" />
      <div class="orb orb-c" />

      <div class="auth-brand-top">
        <BrandLogo tone="light" />
      </div>

      <div class="auth-brand-copy">
        <span class="auth-kicker">AI PERSONALIZED LEARNING</span>
        <h1>让每一次学习<br />都有知识依据</h1>
        <p>
          智课学伴把课程资料、RAG 问答、学习推荐与学情分析连成一个闭环，
          帮助学生学得更准，教师教得更清楚。
        </p>

        <ul class="auth-features">
          <li v-for="item in features" :key="item.title">
            <span class="feature-dot" />
            <div>
              <strong>{{ item.title }}</strong>
              <small>{{ item.text }}</small>
            </div>
          </li>
        </ul>
      </div>

      <div class="auth-brand-footer">
        <!-- <span>本科毕业设计 · 双服务架构</span> -->
        <!-- <span>FastAPI · Vue 3 · RAG</span> -->
      </div>
    </section>

    <section class="auth-panel">
      <div class="auth-panel-inner">
        <router-view />
      </div>
      <p class="auth-copyright">© 2026 智课学伴 EduMate</p>
    </section>
  </div>
</template>

<style scoped>
.auth-shell {
  display: grid;
  min-height: 100vh;
  grid-template-columns: minmax(0, 1.08fr) minmax(420px, 0.92fr);
  background: #fff;
}

.auth-brand {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  overflow: hidden;
  padding: 44px 56px;
  background:
    radial-gradient(circle at 82% 16%, rgba(255, 255, 255, 0.2), transparent 32%),
    linear-gradient(145deg, #0f5fd6 0%, #1677ff 45%, #5aa6ff 100%);
  color: #fff;
}

.orb {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.06);
}

.orb-a {
  width: 380px;
  height: 380px;
  right: -120px;
  top: -90px;
}

.orb-b {
  width: 220px;
  height: 220px;
  right: 90px;
  bottom: 60px;
}

.orb-c {
  width: 90px;
  height: 90px;
  left: 42%;
  top: 34%;
  background: rgba(255, 255, 255, 0.1);
}

.auth-brand-top,
.auth-brand-copy,
.auth-brand-footer {
  position: relative;
  z-index: 1;
}

.auth-brand-copy {
  max-width: 520px;
  margin: 40px 0;
}

.auth-kicker {
  display: inline-flex;
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.auth-brand-copy h1 {
  margin-top: 22px;
  font-size: clamp(38px, 4vw, 54px);
  font-weight: 750;
  line-height: 1.18;
  letter-spacing: -0.035em;
}

.auth-brand-copy > p {
  max-width: 460px;
  margin-top: 18px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 15px;
  line-height: 1.9;
}

.auth-features {
  display: grid;
  gap: 16px;
  margin: 30px 0 0;
  padding: 0;
  list-style: none;
}

.auth-features li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.feature-dot {
  margin-top: 7px;
  width: 8px;
  height: 8px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: #8ff0c8;
  box-shadow: 0 0 0 5px rgba(143, 240, 200, 0.14);
}

.auth-features strong {
  display: block;
  font-size: 14px;
}

.auth-features small {
  display: block;
  margin-top: 2px;
  color: rgba(255, 255, 255, 0.66);
  font-size: 12px;
}

.auth-brand-footer {
  display: flex;
  justify-content: space-between;
  color: rgba(255, 255, 255, 0.55);
  font-size: 12px;
}

.auth-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
  background:
    radial-gradient(circle at 90% 8%, #f2f8ff, transparent 42%),
    #fff;
}

.auth-panel-inner {
  width: 100%;
  max-width: 420px;
}

.auth-copyright {
  margin-top: 44px;
  color: var(--em-text-muted);
  font-size: 12px;
}

@media (max-width: 960px) {
  .auth-shell {
    grid-template-columns: 1fr;
  }

  .auth-brand {
    display: none;
  }

  .auth-panel {
    min-height: 100vh;
    padding: 32px 24px;
  }
}
</style>
