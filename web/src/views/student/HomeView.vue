<script setup>
const stats = [
  { label: '在学课程', value: '—', hint: 'P1.4 接入', icon: 'Notebook', tone: 'blue' },
  { label: '本周问答', value: '—', hint: 'P1.6 接入', icon: 'ChatDotRound', tone: 'green' },
  { label: '推荐资料', value: '—', hint: 'P1.7 接入', icon: 'FolderOpened', tone: 'orange' },
  { label: '平均掌握度', value: '—', hint: '阶段二接入', icon: 'TrendCharts', tone: 'purple' },
]

const tips = [
  '先浏览课程章节，再向 AI 学伴提问，答案会附带资料引用。',
  '问答记录会自动保存，方便复习与追溯知识来源。',
  '完成习题后，系统会更新知识点掌握度并调整推荐。',
]
</script>

<template>
  <div class="em-page student-home">
    <section class="hero em-card">
      <div class="hero-copy">
        <span class="em-eyebrow">STUDENT SPACE</span>
        <h1>你好，同学 👋</h1>
        <p>从课程资料出发，向 AI 学伴提问，让每一次学习都有据可循。</p>
        <div class="hero-actions">
          <router-link to="/student/qa">
            <el-button type="primary" size="large">
              <el-icon><ChatDotRound /></el-icon>
              开始提问
            </el-button>
          </router-link>
          <router-link to="/student/courses">
            <el-button size="large" plain>浏览课程</el-button>
          </router-link>
        </div>
      </div>
      <div class="hero-visual">
        <div class="hero-orbit orbit-one" />
        <div class="hero-orbit orbit-two" />
        <div class="hero-badge">
          <el-icon><Reading /></el-icon>
          <span>知识库问答</span>
        </div>
        <div class="hero-badge hero-badge-alt">
          <el-icon><Aim /></el-icon>
          <span>个性化推荐</span>
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
      <div class="section-card em-card">
        <div class="section-head">
          <div>
            <span class="em-eyebrow">MY COURSES</span>
            <h2>学习课表</h2>
          </div>
          <span class="section-note">P1.4 接入</span>
        </div>
        <div class="empty-state">
          <div class="empty-icon"><el-icon><Notebook /></el-icon></div>
          <h3>还没有课程数据</h3>
          <p>教师发布并通过审核的课程会显示在这里。</p>
          <router-link to="/student/courses">
            <el-button plain type="primary">查看课程入口</el-button>
          </router-link>
        </div>
      </div>

      <div class="section-card em-card">
        <div class="section-head">
          <div>
            <span class="em-eyebrow">RECOMMENDED</span>
            <h2>热门资料</h2>
          </div>
          <span class="section-note">P1.7 接入</span>
        </div>
        <div class="empty-state">
          <div class="empty-icon warm"><el-icon><FolderOpened /></el-icon></div>
          <h3>推荐正在准备</h3>
          <p>浏览与问答行为积累后，这里会出现热门、同章节与相似资料。</p>
        </div>
      </div>
    </section>

    <section class="tips-card em-card">
      <div class="section-head">
        <div>
          <span class="em-eyebrow">LEARNING TIPS</span>
          <h2>学习小贴士</h2>
        </div>
      </div>
      <ul class="tip-list">
        <li v-for="(tip, index) in tips" :key="tip">
          <span class="tip-index">{{ String(index + 1).padStart(2, '0') }}</span>
          <span>{{ tip }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.student-home {
  display: grid;
  gap: 22px;
}

.hero {
  position: relative;
  display: grid;
  min-height: 250px;
  grid-template-columns: minmax(0, 1.2fr) minmax(260px, 0.8fr);
  overflow: hidden;
  padding: 40px 44px;
  background:
    radial-gradient(circle at 88% 18%, rgba(22, 119, 255, 0.14), transparent 34%),
    linear-gradient(135deg, #ffffff, #f2f8ff);
}

.hero-copy h1 {
  margin-top: 10px;
  font-size: 34px;
  font-weight: 760;
  letter-spacing: -0.035em;
}

.hero-copy p {
  max-width: 520px;
  margin-top: 10px;
  color: var(--em-text-secondary);
  font-size: 15px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  margin-top: 26px;
}

.hero-visual {
  position: relative;
  min-height: 160px;
}

.hero-orbit {
  position: absolute;
  border: 1px dashed rgba(22, 119, 255, 0.22);
  border-radius: 50%;
}

.orbit-one {
  width: 220px;
  height: 220px;
  right: 24px;
  top: 0;
}

.orbit-two {
  width: 140px;
  height: 140px;
  right: 64px;
  top: 40px;
}

.hero-badge {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border: 1px solid #d9e9ff;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--em-shadow-card);
  color: #2f5f96;
  font-size: 13px;
  font-weight: 600;
}

.hero-badge .el-icon {
  color: var(--em-primary);
  font-size: 18px;
}

.hero-badge {
  right: 120px;
  top: 42px;
}

.hero-badge-alt {
  right: 30px;
  top: 116px;
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

.tone-blue {
  background: #e8f2ff;
  color: #1677ff;
}

.tone-green {
  background: #e9fbf1;
  color: #16a34a;
}

.tone-orange {
  background: #fff5e6;
  color: #ea8a0a;
}

.tone-purple {
  background: #f1ecff;
  color: #7c5cff;
}

.stat-body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  line-height: 1.3;
}

.stat-body span {
  color: var(--em-text-secondary);
  font-size: 12px;
}

.stat-body strong {
  margin-top: 2px;
  font-size: 24px;
  font-weight: 750;
}

.stat-body small {
  color: var(--em-text-muted);
  font-size: 11px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 0.75fr);
  gap: 18px;
}

.section-card,
.tips-card {
  padding: 24px 26px;
}

.section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.section-head h2 {
  margin-top: 4px;
  font-size: 19px;
  font-weight: 700;
}

.section-note {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f6fd;
  color: #6b7a90;
  font-size: 11px;
}

.empty-state {
  display: flex;
  min-height: 230px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.empty-icon {
  display: grid;
  width: 58px;
  height: 58px;
  place-items: center;
  border-radius: 18px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 25px;
}

.empty-icon.warm {
  background: #fff5e6;
  color: #ea8a0a;
}

.empty-state h3 {
  margin-top: 14px;
  font-size: 16px;
}

.empty-state p {
  max-width: 360px;
  margin: 6px 0 16px;
  color: var(--em-text-secondary);
  font-size: 13px;
}

.tip-list {
  display: grid;
  gap: 12px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}

.tip-list li {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8faff;
  color: #52637a;
}

.tip-index {
  color: var(--em-primary);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 1180px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .hero {
    grid-template-columns: 1fr;
    padding: 28px 24px;
  }

  .hero-visual {
    display: none;
  }

  .stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
