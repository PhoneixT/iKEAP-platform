<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import {
  Plus,
  Play,
  ArrowRight,
  RefreshCw,
  Workflow,
  Bot,
  CircleCheck,
  Terminal,
} from '@lucide/vue';
import { ElMessage } from 'element-plus';
import { orchestrationApi } from '../api';
import { api, post, type Row } from '../../../services/http';
import { useAuth } from '../../../stores/auth';
import StatusTag from '../../../components/StatusTag.vue';
import JsonResult from '../../../components/JsonResult.vue';
const auth = useAuth(),
  tab = ref('workflows'),
  busy = ref(false),
  agents = ref<Row[]>([]),
  workflows = ref<Row[]>([]),
  jobs = ref<Row[]>([]),
  actions = ref<Row[]>([]),
  selectedWorkflow = ref<Row | null>(null),
  job = ref<Row | null>(null),
  drawer = ref(false),
  runDialog = ref(false),
  createDialog = ref('');
const context = ref(
    JSON.stringify(
      {
        query: 'TC4叶盘加工工艺',
        task: 'TC4叶盘工艺规划与刀具选择',
        domain: 'cam',
        parameters: {
          spindle_speed: 3200,
          feed_rate: 600,
          cut_depth: 0.3,
          tool_diameter: 8,
        },
      },
      null,
      2,
    ),
  ),
  form = ref<Row>({}),
  nodes = ref('[]'),
  caps = ref('knowledge.search');
let timer: ReturnType<typeof setInterval>;
async function load() {
  [agents.value, workflows.value, jobs.value, actions.value] = await Promise.all([
    orchestrationApi.agents(),
    orchestrationApi.workflows(),
    orchestrationApi.jobs(),
    api('/agent-orchestration/actions'),
  ]);
}
onMounted(() => {
  load().catch(() => {});
  timer = setInterval(() => {
    if (document.hidden || !jobs.value.some((j) => ['running', 'submitted'].includes(j.status)))
      return;
    orchestrationApi
      .jobs()
      .then((rows) => (jobs.value = rows))
      .catch(() => {});
    if (drawer.value && job.value) inspect(job.value).catch(() => {});
  }, 2500);
});
onUnmounted(() => clearInterval(timer));
async function inspect(row: Row) {
  job.value = await api('/agent-orchestration/jobs/' + row.id);
  drawer.value = true;
}
function showRun(workflow: Row) {
  selectedWorkflow.value = workflow;
  runDialog.value = true;
}
async function run() {
  if (!selectedWorkflow.value) return;
  busy.value = true;
  try {
    const created = await orchestrationApi.run(
      selectedWorkflow.value.id,
      JSON.parse(context.value),
    );
    runDialog.value = false;
    tab.value = 'jobs';
    await load();
    await inspect(created);
    ElMessage.success('任务已提交');
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('上下文必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
function open(kind: string) {
  createDialog.value = kind;
  form.value = {
    name: '',
    description: '',
    protocol: 'internal',
    endpoint: '',
    version: '1.0.0',
  };
  nodes.value = JSON.stringify(
    [
      {
        id: 'search',
        action: 'knowledge.search',
        depends_on: [],
        input: { query: { $ref: 'context.query' } },
      },
    ],
    null,
    2,
  );
}
async function create() {
  busy.value = true;
  try {
    const data =
      createDialog.value === 'agent'
        ? {
            ...form.value,
            capabilities: caps.value
              .split(',')
              .map((c) => c.trim())
              .filter(Boolean),
          }
        : {
            name: form.value.name,
            description: form.value.description,
            nodes: JSON.parse(nodes.value),
          };
    await post(
      '/agent-orchestration/' + (createDialog.value === 'agent' ? 'agents' : 'workflows'),
      data,
    );
    createDialog.value = '';
    await load();
    ElMessage.success('已创建');
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('节点定义必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
async function cancel(row: Row) {
  await post(`/agent-orchestration/jobs/${row.id}/cancel`);
  await load();
  await inspect(row);
}
</script>
<template>
  <div class="protocol-strip">
    <span>
      <Terminal :size="17" />
      MCP
      <b>2025-06-18</b>
      <code>/mcp</code>
    </span>
    <span>
      <Workflow :size="17" />
      A2A
      <b>0.3.0 subset</b>
      <code>/a2a</code>
    </span>
    <span class="muted">统一工具能力与工业任务交换</span>
  </div>
  <section class="panel">
    <el-tabs v-model="tab">
      <el-tab-pane label="流程编排" name="workflows">
        <div class="toolbar">
          <span class="muted">有向无环节点依赖 · 输入引用 · 版本快照</span>
          <el-button v-if="auth.canWrite" type="primary" @click="open('workflow')">
            <Plus :size="16" />
            创建流程
          </el-button>
        </div>
        <article v-for="workflow in workflows" :key="workflow.id" class="workflow-card">
          <div class="toolbar">
            <div>
              <h3>
                {{ workflow.name }}
                <span class="version-pill">v{{ workflow.version }}</span>
              </h3>
              <p class="muted">{{ workflow.description }}</p>
            </div>
            <el-button type="primary" :disabled="!auth.canWrite" @click="showRun(workflow)">
              <Play :size="15" />
              执行流程
            </el-button>
          </div>
          <div class="workflow-nodes">
            <template v-for="(node, index) in workflow.nodes" :key="node.id">
              <ArrowRight v-if="Number(index) > 0" :size="20" class="node-arrow" />
              <div class="workflow-node">
                <span>0{{ Number(index) + 1 }}</span>
                <b>{{ actions.find((a) => a.id === node.action)?.name || node.action }}</b>
                <small>{{ node.id }}</small>
                <code>{{ node.action }}</code>
              </div>
            </template>
          </div>
        </article>
        <el-empty v-if="!workflows.length" description="暂无流程定义" />
      </el-tab-pane>
      <el-tab-pane label="Agent注册中心" name="agents">
        <div class="toolbar">
          <span class="muted">按元数据描述服务能力与支持协议</span>
          <el-button v-if="auth.canWrite" type="primary" @click="open('agent')">
            <Plus :size="16" />
            注册Agent
          </el-button>
        </div>
        <div class="agent-grid">
          <article v-for="agent in agents" :key="agent.id" class="agent-card">
            <div class="agent-icon"><Bot :size="24" /></div>
            <div class="toolbar">
              <h3>{{ agent.name }}</h3>
              <span class="version-pill">v{{ agent.version }}</span>
            </div>
            <p>{{ agent.description }}</p>
            <div class="agent-capabilities">
              <code v-for="capability in agent.capabilities" :key="capability">
                {{ capability }}
              </code>
            </div>
            <small class="muted">
              {{ agent.protocol.toUpperCase() }} {{ agent.endpoint || '平台内部服务' }}
            </small>
          </article>
        </div>
      </el-tab-pane>
      <el-tab-pane label="任务运行" name="jobs">
        <div class="toolbar">
          <span class="muted">任务执行状态与节点产物</span>
          <el-button @click="load">
            <RefreshCw :size="15" />
            刷新
          </el-button>
        </div>
        <el-table :data="jobs">
          <el-table-column prop="name" label="任务" min-width="200" />
          <el-table-column label="状态" width="130">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </el-table-column>
          <el-table-column label="进度" width="180">
            <template #default="{ row }">
              <el-progress :percentage="row.progress" :stroke-width="6" />
            </template>
          </el-table-column>
          <el-table-column label="时间" min-width="190">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150">
            <template #default="{ row }">
              <el-button link type="primary" @click="inspect(row)">详情</el-button>
              <el-button
                v-if="['submitted', 'running'].includes(row.status) && auth.canWrite"
                link
                type="danger"
                @click="cancel(row)"
              >
                取消
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>
  <el-dialog v-model="runDialog" title="执行流程" width="650px">
    <p class="muted">{{ selectedWorkflow?.name }} · 配置节点所需的任务上下文</p>
    <el-input v-model="context" type="textarea" :rows="15" class="code-input" />
    <template #footer>
      <el-button @click="runDialog = false">取消</el-button>
      <el-button type="primary" :loading="busy" @click="run">提交任务</el-button>
    </template>
  </el-dialog>
  <el-dialog
    :model-value="!!createDialog"
    :title="createDialog === 'agent' ? '注册Agent' : '创建流程'"
    width="700px"
    @close="createDialog = ''"
  >
    <el-form label-position="top">
      <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="说明"><el-input v-model="form.description" /></el-form-item>
      <template v-if="createDialog === 'agent'">
        <el-form-item label="能力标签（逗号分隔）"><el-input v-model="caps" /></el-form-item>
        <div class="form-grid">
          <el-form-item label="协议">
            <el-select v-model="form.protocol">
              <el-option v-for="p in ['internal', 'mcp', 'a2a']" :key="p" :value="p" />
            </el-select>
          </el-form-item>
          <el-form-item label="版本"><el-input v-model="form.version" /></el-form-item>
        </div>
        <el-form-item label="服务地址"><el-input v-model="form.endpoint" /></el-form-item>
      </template>
      <template v-else>
        <el-form-item label="节点定义（JSON）">
          <el-input v-model="nodes" type="textarea" :rows="15" class="code-input" />
        </el-form-item>
        <p class="muted">已注册动作：{{ actions.map((a) => a.id).join('、') }}</p>
        <p class="muted">
          输入可使用 {"$ref":"context.query"} 或 {"$ref":"nodes.节点编号.输出字段"} 引用。
        </p>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="createDialog = ''">取消</el-button>
      <el-button type="primary" :loading="busy" @click="create">创建</el-button>
    </template>
  </el-dialog>
  <el-drawer v-model="drawer" title="运行详情" size="760px">
    <template v-if="job">
      <div class="report-heading">
        <h2>{{ job.name }}</h2>
        <StatusTag :value="job.status" />
      </div>
      <p class="muted">{{ job.id }}</p>
      <el-progress :percentage="job.progress" />
      <div v-if="job.error" class="error-note">{{ job.error }}</div>
      <div class="event-timeline">
        <article
          v-for="event in job.events"
          :key="event.id"
          :class="{ 'event-error': event.level === 'error' }"
        >
          <CircleCheck :size="17" />
          <div>
            <b>{{ event.message }}</b>
            <small>{{ new Date(event.created_at).toLocaleTimeString('zh-CN') }}</small>
          </div>
        </article>
      </div>
      <JsonResult :data="job.result" name="workflow-result" />
    </template>
  </el-drawer>
</template>
