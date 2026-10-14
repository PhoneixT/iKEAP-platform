<script setup lang="ts">
import { exportJson } from '../services/http';
defineProps<{ data: any; name?: string }>();
</script>
<template>
  <div class="json-result">
    <div class="toolbar">
      <span class="muted">结果数据</span>
      <el-button size="small" @click="exportJson(name || 'result', data)">导出JSON</el-button>
    </div>
    <details>
      <summary>展开结构化数据</summary>
      <pre>{{ JSON.stringify(data, null, 2) }}</pre>
    </details>
  </div>
</template>
