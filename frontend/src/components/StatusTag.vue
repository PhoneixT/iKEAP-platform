<script setup lang="ts">
import { computed } from 'vue';
const props = defineProps<{ value: string }>();
const labels: Record<string, string> = {
  passed: '通过',
  failed: '失败',
  unknown: '待确认',
  submitted: '已提交',
  running: '运行中',
  completed: '已完成',
  cancelled: '已取消',
  draft: '待规划',
  planned: '已规划',
  demonstrated: '演示完成',
  simulated: '仿真通过',
  approved: '已审核',
  dispatched: '已分发',
  needs_review: '待复核',
  open: '待分析',
  diagnosed: '已分析',
  closed: '已关闭',
  pending: '待执行',
  in_progress: '处理中',
  available: '可用',
  offline: '离线',
  maintenance: '维护中',
  high: '高',
  medium: '中',
  low: '低',
  estimated: '趋势估计',
  threshold_reached: '已达阈值',
  insufficient_data: '数据不足',
  not_predictable: '不可预测',
};
const color = computed(() =>
  ['passed', 'completed', 'available', 'closed', 'approved', 'simulated'].includes(props.value)
    ? 'green'
    : ['failed', 'high', 'needs_review', 'threshold_reached'].includes(props.value)
      ? 'red'
      : ['running', 'planned', 'diagnosed', 'dispatched', 'in_progress'].includes(props.value)
        ? 'blue'
        : 'amber',
);
</script>
<template>
  <span :class="['status-tag', color]">
    <i />
    {{ labels[value] || value }}
  </span>
</template>
