<script setup>
const stats = [
  { label: '我的课程', value: '—', hint: 'P1.4 接入', icon: 'Notebook', tone: 'blue' },
  { label: '待审核资料', value: '—', hint: 'P1.5 接入', icon: 'DocumentChecked', tone: 'orange' },
  { label: '学生提问', value: '—', hint: 'P1.6 接入', icon: 'ChatDotRound', tone: 'green' },
  { label: '平均掌握度', value: '—', hint: '阶段二接入', icon: 'TrendCharts', tone: 'purple' },
]

const actions = [
  { title: '创建课程', text: '搭建章节与知识点，提交管理员审核', path: '/teacher/courses', icon: 'Plus' },
  { title: '上传资料', text: '上传课件，审核通过后自动建立 RAG 索引', path: '/teacher/materials', icon: 'UploadFilled' },
  { title: '查看学情', text: '了解班级掌握度、薄弱知识点与高频问题', path: '/teacher/analytics', icon: 'DataAnalysis' },
]
</script>

<template>
  <div class="em-page teacher-home">
    <section class="hero em-card">
      <div>
        <span class="em-eyebrow">TEACHER WORKSPACE</span>
        <h1>教学工作台</h1>
        <p>管理课程与资料，观察学生学习状态，让教学内容持续迭代。</p>
      </div>
      <div class="hero-actions">
        <router-link to="/teacher/courses">
          <el-button type="primary" size="large">
            <el-icon><Plus /></el-icon>
            创建课程
          </el-button>
        </router-link>
        <router-link to="/teacher/materials">
          <el-button size="large" plain>上传资料</el-button>
        </router-link>
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

    <section class="action-grid">
      <router-link v-for="item in actions" :key="item.title" :to="item.path" class="action-card em-card">
        <div class="action-icon"><el-icon><component :is="item.icon" /></el-icon></div>
        <div>
          <h3>{{ item.title }}</h3>
          <p>{{ item.text }}</p>
        </div>
        <el-icon class="action-arrow"><ArrowRight /></el-icon>
      </router-link>
    </section>

    <section class="recent em-card">
      <div class="section-head">
        <div>
          <span class="em-eyebrow">RECENT ACTIVITY</span>
          <h2>最近动态</h2>
        </div>
        <span class="section-note">P1.5 接入</span>
      </div>
      <el-empty description="暂无教学动态，创建课程或上传资料后会显示在这里。" />
    </section>
  </div>
</template>

<style scoped>
.teacher-home {
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
    radial-gradient(circle at 92% 10%, rgba(34, 197, 94, 0.1), transparent 34%),
    linear-gradient(135deg, #ffffff, #f4fbf7);
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

.hero-actions {
  display: flex;
  gap: 12px;
  flex: 0 0 auto;
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

.action-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.action-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px;
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.action-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--em-shadow-float);
}

.action-icon {
  display: grid;
  width: 50px;
  height: 50px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 15px;
  background: var(--em-primary-soft);
  color: var(--em-primary);
  font-size: 22px;
}

.action-card h3 {
  font-size: 16px;
}

.action-card p {
  margin-top: 4px;
  color: var(--em-text-secondary);
  font-size: 12px;
}

.action-arrow {
  margin-left: auto;
  color: var(--em-text-muted);
}

.recent {
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

.section-note {
  padding: 4px 10px;
  border-radius: 999px;
  background: #f1f6fd;
  color: #6b7a90;
  font-size: 11px;
}

@media (max-width: 1180px) {
  .stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .action-grid { grid-template-columns: 1fr; }
}

@media (max-width: 760px) {
  .hero { flex-direction: column; align-items: flex-start; }
  .stat-grid { grid-template-columns: 1fr; }
}
</style>
