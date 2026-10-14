import type { RouteRecordRaw } from 'vue-router';
export default [
  {
    path: 'blisk-cam',
    component: () => import('./views/Cam.vue'),
    meta: { title: '叶盘CAM', subtitle: '工艺规划、工程验证与执行反馈' },
  },
] satisfies RouteRecordRaw[];
