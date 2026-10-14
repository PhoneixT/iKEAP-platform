<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  ArrowUpRight,
  Network,
  ShieldCheck,
  Workflow,
  Activity,
  ArrowRight,
  Box,
  Layers,
} from '@lucide/vue';
import { api, type Row } from '../../../services/http';
import StatusTag from '../../../components/StatusTag.vue';
const data = ref<Row | null>(null),
  loading = ref(false);
async function load() {
  loading.value = true;
  try {
    data.value = await api('/platform/overview');
  } finally {
    loading.value = false;
  }
}
onMounted(load);
const cards = [
  {
    key: 'entities',
    title: '知识实体',
    icon: Network,
    label: '工业知识图谱',
    path: '/knowledge-graph',
  },
  {
    key: 'reasoning_runs',
    title: '推理任务',
    icon: Layers,
    label: '方案与检索证据',
    path: '/hybrid-reasoning',
  },
  {
    key: 'validation_reports',
    title: '验证报告',
    icon: ShieldCheck,
    label: '工程约束检查',
    path: '/constraint-validation',
  },
  {
    key: 'open_anomalies',
    title: '待处理异常',
    icon: Activity,
    label: '设备健康监测',
    path: '/cnc-phm',
  },
];
</script>
<template>
  <div v-loading="loading">
    <section class="welcome-panel">
      <div>
        <span class="section-kicker">工业任务协同</span>
        <h2>从知识出发，让工程任务形成闭环</h2>
        <p>统一组织资源接入、知识检索、方案推理、工程验证与执行反馈。</p>
        <RouterLink to="/agent-orchestration" class="welcome-link">
          进入任务编排
          <ArrowRight :size="16" />
        </RouterLink>
      </div>
      <div class="welcome-network">
        <span>KNOWLEDGE</span>
        <span>MODEL</span>
        <strong>iKEAP</strong>
        <span>DATA</span>
        <span>RESOURCE</span>
      </div>
    </section>
    <div class="stats-grid">
      <RouterLink v-for="card in cards" :key="card.key" :to="card.path" class="stat-card">
        <div class="stat-top">
          <span>{{ card.title }}</span>
          <component :is="card.icon" :size="19" />
        </div>
        <strong>{{ data?.counts[card.key] ?? '—' }}</strong>
        <div class="stat-bottom">
          {{ card.label }}
          <ArrowUpRight :size="16" />
        </div>
      </RouterLink>
    </div>
    <div class="dashboard-columns">
      <section class="panel">
        <div class="panel-header">
          <h3>工程应用</h3>
          <span class="muted">APPLICATIONS</span>
        </div>
        <div class="application-card">
          <div class="app-tile blue"><Box :size="28" /></div>
          <div>
            <h4>叶盘CAM工作流</h4>
            <p>工艺规划 / 刀路接口 / 仿真验证 / 执行反馈</p>
            <small>{{ data?.counts.cam_projects ?? 0 }} 个加工项目</small>
          </div>
          <RouterLink to="/blisk-cam" class="round-link" aria-label="进入叶盘CAM">
            <ArrowUpRight :size="20" />
          </RouterLink>
        </div>
        <div class="application-card">
          <div class="app-tile teal"><Activity :size="28" /></div>
          <div>
            <h4>数控机床PHM</h4>
            <p>异常分析 / 故障检索 / 趋势估计 / 维护决策</p>
            <small>
              {{ data?.counts.machines ?? 0 }} 台设备 ·
              {{ data?.counts.open_anomalies ?? 0 }} 个待处理事件
            </small>
          </div>
          <RouterLink to="/cnc-phm" class="round-link" aria-label="进入机床PHM">
            <ArrowUpRight :size="20" />
          </RouterLink>
        </div>
      </section>
      <section class="panel architecture-panel">
        <div class="panel-header">
          <h3>平台架构</h3>
          <span class="muted">4 LAYERS</span>
        </div>
        <div
          v-for="(layer, index) in [...(data?.architecture || [])].reverse()"
          :key="layer.name"
          class="architecture-layer"
        >
          <span>0{{ 4 - index }}</span>
          <b>{{ layer.name }}</b>
          <small>{{ layer.description }}</small>
        </div>
        <p class="architecture-note">
          <span class="dot" />
          知识—模型—数据—资源协同闭环
        </p>
      </section>
    </div>
    <section class="panel">
      <div class="panel-header">
        <h3>
          最近任务
          <span class="count-pill">{{ data?.recent_jobs.length || 0 }}</span>
        </h3>
        <RouterLink to="/agent-orchestration" class="text-link">
          查看全部
          <ArrowRight :size="14" />
        </RouterLink>
      </div>
      <el-table
        :data="data?.recent_jobs || []"
        empty-text="暂无运行记录，前往Agent与编排执行首个流程"
      >
        <el-table-column prop="name" label="任务名称" min-width="220" />
        <el-table-column label="所属模块" min-width="180">
          <template #default>Agent协同编排</template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }"><StatusTag :value="row.status" /></template>
        </el-table-column>
        <el-table-column label="进度" width="160">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="5" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="190">
          <template #default="{ row }">
            {{ new Date(row.created_at).toLocaleString('zh-CN') }}
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>
