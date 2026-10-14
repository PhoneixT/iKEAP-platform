import type { RouteRecordRaw } from 'vue-router';
export default [
  {
    path: '',
    name: 'overview',
    component: () => import('./views/Dashboard.vue'),
    meta: { title: '工作台', subtitle: '平台运行概览与工业任务入口' },
  },
  {
    path: 'platform',
    component: () => import('./views/Platform.vue'),
    meta: { title: '平台管理', subtitle: '资源、服务、账户与操作审计' },
  },
] satisfies RouteRecordRaw[];
