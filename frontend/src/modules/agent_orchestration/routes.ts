import type { RouteRecordRaw } from 'vue-router';
export default [
  {
    path: 'agent-orchestration',
    component: () => import('./views/Orchestration.vue'),
    meta: { title: 'Agent与编排', subtitle: '能力发现、流程定义与执行追踪' },
  },
] satisfies RouteRecordRaw[];
