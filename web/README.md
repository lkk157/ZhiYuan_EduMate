# EduMate Web

Vue 3 + Vite + Element Plus 前端。

## 开发

```bash
npm install
npm run dev      # http://localhost:5173，/api 代理到 http://127.0.0.1:8001
```

## 测试与构建

```bash
npm run test:unit -- --run
npm run build
```

## 结构

```
src/
  api/        Axios 实例与接口模块
  components/  通用组件（品牌标识、占位页）
  layouts/     AuthLayout / MainLayout
  router/      三角色路由与守卫
  stores/      Pinia（认证）
  styles/      设计变量与全局样式
  utils/       角色与菜单配置
  views/       登录、404、学生/教师/管理员页面
tests/         Vitest 单元测试
```

## 视觉规范

主色 `#1677ff`，背景 `#f5f7fb`，白色 16px 圆角卡片；左侧 220px 侧栏，选中项蓝色圆角块。参考项目规划中的效果图。
