import type { RouteRecordRaw } from 'vue-router';
export default [
  {
    path: 'knowledge-graph',
    component: () => import('./views/Knowledge.vue'),
    meta: { title: '知识中心', subtitle: '实体、关系与可追溯的检索证据' },
  },
] satisfies RouteRecordRaw[];
