<script setup lang="ts">
import { computed } from 'vue';
import type { Row } from '../../../services/http';
const props = defineProps<{
  samples: Row[];
  field: string;
  threshold?: number;
  unit: string;
}>();
const values = computed(() => props.samples.map((p) => Number(p[props.field])));
const max = computed(() => Math.max(...values.value, props.threshold || 0, 1) * 1.2);
const plot = computed(() =>
  values.value
    .map(
      (v, i) =>
        `${45 + (i / Math.max(1, values.value.length - 1)) * 690},${195 - (v / max.value) * 155}`,
    )
    .join(' '),
);
const thresholdY = computed(() => 195 - ((props.threshold || 0) / max.value) * 155);
</script>
<template>
  <div class="trend-chart">
    <svg viewBox="0 0 770 235" role="img" :aria-label="`${field}趋势图`">
      <defs>
        <linearGradient :id="'trend-fill-' + field" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#168f87" stop-opacity=".2" />
          <stop offset="100%" stop-color="#168f87" stop-opacity="0" />
        </linearGradient>
      </defs>
      <g v-for="i in 5" :key="i">
        <line
          x1="45"
          :y1="40 + (i - 1) * 38.75"
          x2="735"
          :y2="40 + (i - 1) * 38.75"
          stroke="#e8edef"
          stroke-dasharray="3 4"
        />
        <text x="33" :y="44 + (i - 1) * 38.75" text-anchor="end" fill="#95a4aa" font-size="10">
          {{ ((max * (5 - i)) / 4).toFixed(1) }}
        </text>
      </g>
      <text x="45" y="20" fill="#83979e" font-size="11">{{ unit }}</text>
      <polygon
        v-if="values.length"
        :points="`45,195 ${plot} 735,195`"
        :fill="`url(#trend-fill-${field})`"
      />
      <polyline
        :points="plot"
        fill="none"
        stroke="#168f87"
        stroke-width="2.5"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
      <g v-if="threshold">
        <line
          x1="45"
          :y1="thresholdY"
          x2="735"
          :y2="thresholdY"
          stroke="#d19a4a"
          stroke-width="1.3"
          stroke-dasharray="6 4"
        />
        <text x="734" :y="thresholdY - 7" text-anchor="end" fill="#bb8541" font-size="10">
          阈值 {{ threshold }}
        </text>
      </g>
      <text x="45" y="218" fill="#94a2a8" font-size="10">
        {{ samples[0] ? new Date(samples[0].time).toLocaleString('zh-CN') : '' }}
      </text>
      <text x="735" y="218" text-anchor="end" fill="#94a2a8" font-size="10">
        {{ samples.at(-1) ? new Date(samples.at(-1)!.time).toLocaleString('zh-CN') : '' }}
      </text>
    </svg>
    <el-empty v-if="!values.length" description="暂无采样数据" />
  </div>
</template>
