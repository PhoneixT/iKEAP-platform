<script setup lang="ts">
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { Cpu, ArrowRight, Network, ShieldCheck, Workflow } from '@lucide/vue';
import { useAuth } from '../../../stores/auth';
const router = useRouter(),
  auth = useAuth(),
  busy = ref(false);
const username = ref('admin'),
  password = ref('');
async function submit() {
  if (!username.value || !password.value) return;
  busy.value = true;
  try {
    await auth.login(username.value, password.value);
    await router.push('/');
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="login-page">
    <section class="login-story">
      <div class="login-logo">
        <Cpu :size="30" />
        iKEAP
        <span>工业软件云平台</span>
      </div>
      <div class="login-story-main">
        <div class="eyebrow">INDUSTRIAL KNOWLEDGE & ENGINEERING</div>
        <h1>
          让工业知识
          <br />
          贯通工程任务。
        </h1>
        <p>
          连接知识、模型、数据与资源，
          <br />
          构建从方案到验证、从执行到反馈的协同闭环。
        </p>
        <div class="login-pillars">
          <span>
            <Network :size="19" />
            知识与检索
          </span>
          <span>
            <ShieldCheck :size="19" />
            工程验证
          </span>
          <span>
            <Workflow :size="19" />
            任务协同
          </span>
        </div>
        <div class="orbit">
          <div class="orbit-ring" />
          <div class="orbit-ring inner" />
          <div class="orbit-core">iK</div>
          <span class="orbit-node n1">知识</span>
          <span class="orbit-node n2">模型</span>
          <span class="orbit-node n3">数据</span>
          <span class="orbit-node n4">资源</span>
        </div>
      </div>
      <small>iKEAP-platform / v1.0</small>
    </section>
    <section class="login-form">
      <form @submit.prevent="submit">
        <div class="eyebrow">WELCOME TO iKEAP</div>
        <h2>登录工作空间</h2>
        <p class="muted">使用平台账户开始工业协同任务</p>
        <label for="username">用户名</label>
        <el-input
          id="username"
          v-model="username"
          size="large"
          autocomplete="username"
          placeholder="请输入用户名"
        />
        <label for="password">密码</label>
        <el-input
          id="password"
          v-model="password"
          type="password"
          size="large"
          show-password
          autocomplete="current-password"
          placeholder="请输入登录密码"
        />
        <el-button
          class="login-submit"
          type="primary"
          size="large"
          native-type="submit"
          :loading="busy"
        >
          登录平台
          <ArrowRight :size="17" />
        </el-button>
        <p class="login-hint">初始账户由部署配置创建，请向平台管理员获取登录信息。</p>
      </form>
    </section>
  </div>
</template>
