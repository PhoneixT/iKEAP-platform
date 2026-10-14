<script setup lang="ts">
import { computed, ref } from 'vue';
import type { Row } from '../../../services/http';
const props = defineProps<{ graph: { nodes: Row[]; edges: Row[] } }>();
const emit = defineEmits<{ select: [node: Row] }>();
const active = ref(''),
  zoom = ref(1);
const colors: Record<string, string> = {
  材料: '#9c78c9',
  零件: '#159a8b',
  设备: '#5388c9',
  刀具: '#d69b43',
  工艺: '#3f91a6',
  验证: '#c47684',
  部件: '#6472b8',
  故障: '#dc7961',
  症状: '#ca9b48',
  维护: '#6ba78f',
};
const nodes = computed<Row[]>(() =>
  props.graph.nodes.map((node, index, all) => {
    const angle = (index * Math.PI * 2) / all.length - Math.PI / 2;
    const radius = all.length < 4 ? 105 : index % 3 === 0 ? 125 : 195;
    return {
      ...node,
      x: 420 + Math.cos(angle) * radius * 1.45,
      y: 265 + Math.sin(angle) * radius,
      color: colors[node.kind] || '#658e9e',
    };
  }),
);
const edges = computed<Row[]>(() =>
  props.graph.edges
    .map((edge) => ({
      ...edge,
      from: nodes.value.find((n) => n.id === edge.source_id),
      to: nodes.value.find((n) => n.id === edge.target_id),
    }))
    .filter((edge) => edge.from && edge.to),
);
function select(node: Row) {
  active.value = node.id;
  emit('select', node);
}
</script>
<template>
  <div class="graph-canvas">
    <div class="graph-tools">
      <button @click="zoom = Math.min(1.7, zoom + 0.15)" aria-label="放大图谱">+</button>
      <button @click="zoom = Math.max(0.6, zoom - 0.15)" aria-label="缩小图谱">−</button>
      <button
        @click="
          zoom = 1;
          active = '';
        "
        aria-label="重置图谱"
      >
        ↺
      </button>
    </div>
    <svg viewBox="0 0 840 530" role="img" aria-label="工业知识实体关系图">
      <defs>
        <pattern id="graph-dots" width="22" height="22" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="1" fill="#dce4e7" />
        </pattern>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="21"
          refY="5"
          markerWidth="5"
          markerHeight="5"
          orient="auto-start-reverse"
        >
          <path d="M0 0L10 5L0 10Z" fill="#b7c7cc" />
        </marker>
      </defs>
      <rect width="840" height="530" fill="url(#graph-dots)" />
      <g :transform="`translate(${420 * (1 - zoom)} ${265 * (1 - zoom)}) scale(${zoom})`">
        <g
          v-for="edge in edges"
          :key="edge.id"
          :opacity="active && edge.source_id !== active && edge.target_id !== active ? 0.15 : 1"
        >
          <line
            :x1="edge.from!.x"
            :y1="edge.from!.y"
            :x2="edge.to!.x"
            :y2="edge.to!.y"
            stroke="#bdcdd2"
            stroke-width="1.3"
            marker-end="url(#arrow)"
          />
          <text
            :x="(edge.from!.x + edge.to!.x) / 2"
            :y="(edge.from!.y + edge.to!.y) / 2 - 5"
            text-anchor="middle"
            font-size="10"
            fill="#8b9ca2"
            stroke="#fafcfc"
            stroke-width="3"
            paint-order="stroke"
          >
            {{ edge.kind }}
          </text>
        </g>
        <g
          v-for="node in nodes"
          :key="node.id"
          class="graph-node"
          role="button"
          tabindex="0"
          :aria-label="node.name"
          @click="select(node)"
          @keydown.enter="select(node)"
        >
          <circle
            :cx="node.x"
            :cy="node.y"
            :r="active === node.id ? 26 : 22"
            :fill="node.color + '1c'"
            :stroke="node.color"
            :stroke-width="active === node.id ? 2.5 : 1"
          />
          <circle :cx="node.x" :cy="node.y" r="6" :fill="node.color" />
          <text
            :x="node.x"
            :y="node.y + 38"
            text-anchor="middle"
            fill="#354e58"
            font-size="12"
            font-weight="500"
          >
            {{ node.name }}
          </text>
          <title>{{ node.kind }}：{{ node.description }}</title>
        </g>
      </g>
    </svg>
    <div class="graph-caption">
      {{ graph.nodes.length }} 个实体 · {{ graph.edges.length }} 条关系
      <span>点击实体查看来源与属性</span>
    </div>
    <el-empty v-if="!graph.nodes.length" description="暂无图谱数据" />
  </div>
</template>
