import type { RouteRecordRaw } from 'vue-router';
export default [
  {
    path: 'constraint-validation',
    component: () => import('./views/Validation.vue'),
    meta: { title: '约束验证', subtitle: '规则、工业参数与资源能力检查' },
  },
] satisfies RouteRecordRaw[];
