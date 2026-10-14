import type { RouteRecordRaw } from 'vue-router';
export default [
  {
    path: 'cnc-phm',
    component: () => import('./views/Phm.vue'),
    meta: { title: '机床PHM', subtitle: '异常分析、健康趋势与维护闭环' },
  },
] satisfies RouteRecordRaw[];
