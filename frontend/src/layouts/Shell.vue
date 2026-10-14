<script setup lang="ts">
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import {
  LayoutDashboard,
  Network,
  Layers,
  ShieldCheck,
  Workflow,
  Box,
  Activity,
  Settings2,
  LogOut,
  ChevronRight,
  CircleHelp,
  Bell,
  Cpu,
} from '@lucide/vue';
import { useAuth } from '../stores/auth';
const route = useRoute(),
  router = useRouter(),
  auth = useAuth();
const nav = [
  { path: '/', name: '工作台', icon: LayoutDashboard },
  { path: '/knowledge-graph', name: '知识中心', icon: Network, number: '01' },
  { path: '/hybrid-reasoning', name: '协同推理', icon: Layers, number: '02' },
  {
    path: '/constraint-validation',
    name: '约束验证',
    icon: ShieldCheck,
    number: '03',
  },
  {
    path: '/agent-orchestration',
    name: 'Agent与编排',
    icon: Workflow,
    number: '04',
  },
  { path: '/blisk-cam', name: '叶盘CAM', icon: Box, number: '05' },
  { path: '/cnc-phm', name: '机床PHM', icon: Activity, number: '06' },
  { path: '/platform', name: '平台管理', icon: Settings2 },
];
onMounted(() => auth.load().catch(() => router.push('/login')));
function logout() {
  auth.logout();
  router.push('/login');
}
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink to="/" class="brand">
        <span class="brand-symbol"><Cpu :size="24" /></span>
        <span>
          <b>iKEAP</b>
          <small>工业软件云平台</small>
        </span>
      </RouterLink>
      <div class="workspace-label">
        <span class="dot" />
        工业协同工作空间
        <ChevronRight :size="14" />
      </div>
      <div class="nav-label">工作空间 / WORKSPACE</div>
      <nav>
        <RouterLink
          v-for="item in nav"
          :key="item.path"
          :to="item.path"
          :class="['nav-item', { selected: route.path === item.path }]"
          :aria-current="route.path === item.path ? 'page' : undefined"
        >
          <component :is="item.icon" :size="18" />
          <span>{{ item.name }}</span>
          <small v-if="item.number">{{ item.number }}</small>
        </RouterLink>
      </nav>
      <div class="sidebar-bottom">
        <div class="system-mark">
          <span class="dot" />
          工业任务协同平台
          <span>v1.0</span>
        </div>
        <div class="profile">
          <div class="avatar">
            {{ auth.user?.display_name?.slice(0, 1) || '用' }}
          </div>
          <div>
            <b>{{ auth.user?.display_name || '加载中' }}</b>
            <small>
              {{
                auth.user?.role === 'admin'
                  ? '平台管理员'
                  : auth.user?.role === 'viewer'
                    ? '查看者'
                    : '工程师'
              }}
            </small>
          </div>
          <button class="icon-button" aria-label="退出登录" title="退出登录" @click="logout">
            <LogOut :size="17" />
          </button>
        </div>
      </div>
    </aside>
    <div class="main-shell">
      <header class="topbar">
        <div class="breadcrumb">
          工作空间
          <ChevronRight :size="14" />
          <strong>{{ route.meta.title }}</strong>
        </div>
        <div class="topbar-right">
          <span class="env-badge">本地工作环境</span>
          <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noopener" title="接口文档">
            <CircleHelp :size="18" />
          </a>
          <RouterLink to="/agent-orchestration" title="任务记录"><Bell :size="18" /></RouterLink>
          <span class="topbar-divider" />
          <span>{{ new Date().toLocaleDateString('zh-CN') }}</span>
        </div>
      </header>
      <main>
        <div class="page-heading">
          <div>
            <div class="eyebrow">iKEAP / INDUSTRIAL COLLABORATION</div>
            <h1>{{ route.meta.title }}</h1>
            <p>{{ route.meta.subtitle }}</p>
          </div>
          <span class="heading-code">
            {{
              route.path === '/'
                ? 'OVERVIEW'
                : route.path.slice(1).replaceAll('-', ' ').toUpperCase()
            }}
          </span>
        </div>
        <RouterView />
      </main>
      <footer>
        <span>iKEAP-platform · 工业软件云平台</span>
        <span>知识 / 模型 / 数据 / 资源</span>
      </footer>
    </div>
  </div>
</template>
