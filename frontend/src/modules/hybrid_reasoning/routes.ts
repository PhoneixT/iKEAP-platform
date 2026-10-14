import type { RouteRecordRaw } from 'vue-router';
export default [
  {
    path: 'hybrid-reasoning',
    component: () => import('./views/Reasoning.vue'),
    meta: { title: '协同推理', subtitle: '从工业任务到有据可查的候选方案' },
  },
] satisfies RouteRecordRaw[];
