<script setup lang="ts">
import { onMounted, ref } from 'vue';
import {
  Plus,
  Box,
  ArrowRight,
  FileCheck2,
  Send,
  MessageSquare,
  Layers,
  Download,
  Play,
} from '@lucide/vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { camApi } from '../api';
import { api, post, exportJson, type Row } from '../../../services/http';
import { useAuth } from '../../../stores/auth';
import StatusTag from '../../../components/StatusTag.vue';
import JsonResult from '../../../components/JsonResult.vue';
const auth = useAuth(),
  projects = ref<Row[]>([]),
  resources = ref<Row[]>([]),
  files = ref<Row[]>([]),
  selected = ref<Row | null>(null),
  busy = ref(false),
  dialog = ref(false),
  feedbackDialog = ref(false),
  tab = ref('plan'),
  form = ref<Row>({}),
  simulationMode = ref('demonstration'),
  feedback = ref({ operator: '', accepted: true, notes: '' });
async function load() {
  [projects.value, resources.value, files.value] = await Promise.all([
    camApi.projects(),
    api('/platform/resources'),
    api('/platform/files'),
  ]);
  if (selected.value)
    selected.value = projects.value.find((p) => p.id === selected.value!.id) || null;
  else selected.value = projects.value[0] || null;
}
onMounted(() => load().catch(() => {}));
function open() {
  form.value = {
    name: '',
    material: 'TC4',
    description: '',
    geometry_file_id: '',
    resource_id: resources.value[0]?.id || '',
    parameters: {
      spindle_speed: 3200,
      feed_rate: 600,
      cut_depth: 0.3,
      tool_diameter: 8,
    },
  };
  dialog.value = true;
}
async function create() {
  busy.value = true;
  try {
    selected.value = await post('/blisk-cam/projects', {
      ...form.value,
      resource_id: form.value.resource_id || null,
      geometry_file_id: form.value.geometry_file_id || null,
    });
    dialog.value = false;
    await load();
    ElMessage.success('项目已创建');
  } catch {
  } finally {
    busy.value = false;
  }
}
async function act(action: string, body: any = {}) {
  if (!selected.value) return;
  busy.value = true;
  try {
    selected.value = await camApi.action(selected.value.id, action, body);
    await load();
    ElMessage.success('操作完成');
  } catch {
  } finally {
    busy.value = false;
  }
}
async function approve() {
  try {
    await ElMessageBox.confirm('确认当前版本的工程仿真与程序已完成复核？', '工程审核', {
      type: 'warning',
    });
    await act('approve');
  } catch {}
}
async function dispatch() {
  try {
    await ElMessageBox.confirm('程序将发送到项目绑定的设备资源，确认分发？', '程序分发', {
      type: 'warning',
    });
    await act('dispatch');
  } catch {}
}
async function submitFeedback() {
  await act('feedback', feedback.value);
  if (selected.value?.status !== 'dispatched') feedbackDialog.value = false;
}
const units: Record<string, string> = {
  spindle_speed: 'rpm',
  feed_rate: 'mm/min',
  cut_depth: 'mm',
  tool_diameter: 'mm',
};
const names: Record<string, string> = {
  spindle_speed: '主轴转速',
  feed_rate: '进给速度',
  cut_depth: '切削深度',
  tool_diameter: '刀具直径',
};
</script>
<template>
  <div class="toolbar page-toolbar">
    <span class="muted">{{ projects.length }} 个加工项目</span>
    <el-button v-if="auth.canWrite" type="primary" @click="open">
      <Plus :size="16" />
      新建加工项目
    </el-button>
  </div>
  <div class="master-detail">
    <aside class="panel project-list">
      <div class="panel-header">
        <h3>加工项目</h3>
        <Box :size="18" />
      </div>
      <button
        v-for="project in projects"
        :key="project.id"
        :class="['project-list-item', { active: selected?.id === project.id }]"
        @click="selected = project"
      >
        <span class="project-code">{{ project.material }} / BLISK</span>
        <b>{{ project.name }}</b>
        <div>
          <StatusTag :value="project.status" />
          <small>{{ new Date(project.created_at).toLocaleDateString('zh-CN') }}</small>
        </div>
      </button>
      <el-empty v-if="!projects.length" description="暂无加工项目" />
    </aside>
    <section class="panel project-detail" v-loading="busy">
      <template v-if="selected">
        <div class="report-heading">
          <div>
            <span class="section-kicker">MANUFACTURING PROJECT</span>
            <h2>{{ selected.name }}</h2>
            <p class="muted">{{ selected.description }}</p>
          </div>
          <StatusTag :value="selected.status" />
        </div>
        <div class="process-strip">
          <span>工艺规划</span>
          <ArrowRight :size="14" />
          <span>参数验证</span>
          <ArrowRight :size="14" />
          <span>刀路与仿真</span>
          <ArrowRight :size="14" />
          <span>审核分发</span>
          <ArrowRight :size="14" />
          <span>执行反馈</span>
        </div>
        <div class="parameter-grid">
          <div v-for="(value, key) in selected.parameters" :key="key">
            <small>{{ names[key] || key }}</small>
            <b>
              {{ value }}
              <em>{{ units[key] }}</em>
            </b>
          </div>
        </div>
        <div class="resource-line">
          <Layers :size="15" />
          {{ resources.find((r) => r.id === selected?.resource_id)?.name || '尚未关联资源' }}
          <span>材料：{{ selected.material }}</span>
        </div>
        <el-tabs v-model="tab">
          <el-tab-pane label="工艺方案" name="plan">
            <div class="toolbar">
              <span class="muted">工序组织与候选方案验证</span>
              <el-button
                :disabled="
                  !auth.canWrite ||
                  ['approved', 'dispatched', 'completed'].includes(selected.status)
                "
                type="primary"
                @click="act('plan')"
              >
                <Play :size="15" />
                {{ selected.plan.operations ? '重新规划' : '生成工艺方案' }}
              </el-button>
            </div>
            <template v-if="selected.plan.operations">
              <div class="info-note">
                {{ selected.plan.source }} · 切削速度 {{ selected.plan.cutting_speed_m_min }} m/min
              </div>
              <div
                v-for="operation in selected.plan.operations"
                :key="operation.sequence"
                class="operation-row"
              >
                <span>{{ String(operation.sequence).padStart(2, '0') }}</span>
                <div>
                  <h4>{{ operation.name }}</h4>
                  <small>{{ operation.strategy }}</small>
                </div>
                <FileCheck2 :size="18" />
              </div>
              <div class="toolbar">
                <span>工艺参数验证</span>
                <StatusTag :value="selected.plan.validation.status" />
              </div>
              <el-table :data="selected.plan.validation.findings">
                <el-table-column prop="rule_name" label="检查项" min-width="170" />
                <el-table-column label="实际值" width="140">
                  <template #default="{ row }">{{ row.value }} {{ row.unit }}</template>
                </el-table-column>
                <el-table-column label="结果" width="110">
                  <template #default="{ row }"><StatusTag :value="row.status" /></template>
                </el-table-column>
              </el-table>
            </template>
            <el-empty v-else description="生成工艺方案后查看工序与参数验证结果" />
          </el-tab-pane>
          <el-tab-pane label="工程服务" name="simulation">
            <div class="info-note">
              演示模式仅验证接口流转，不执行几何仿真。真实模式需配置CAM工程服务，并返回当前输入版本的仿真结果和程序。
            </div>
            <div class="toolbar">
              <el-radio-group v-model="simulationMode">
                <el-radio-button value="demonstration">流程演示</el-radio-button>
                <el-radio-button value="external">真实工程服务</el-radio-button>
              </el-radio-group>
              <el-button
                type="primary"
                :disabled="
                  !auth.canWrite ||
                  !['planned', 'demonstrated', 'simulated'].includes(selected.status)
                "
                @click="act('simulate', { mode: simulationMode })"
              >
                执行验证调用
              </el-button>
            </div>
            <div class="button-group spaced">
              <el-button
                :disabled="!auth.canWrite || !['planned', 'demonstrated'].includes(selected.status)"
                @click="act('algorithm', { mode: 'local', engagement_width_mm: 1 })"
              >
                运行参数比选
              </el-button>
              <el-button
                :disabled="!auth.canWrite || !['planned', 'demonstrated'].includes(selected.status)"
                @click="act('algorithm', { mode: 'external', engagement_width_mm: 1 })"
              >
                调用元算法服务
              </el-button>
              <el-button
                :disabled="
                  !auth.canWrite ||
                  !selected.geometry_file_id ||
                  !['planned', 'demonstrated'].includes(selected.status)
                "
                @click="act('toolpath')"
              >
                生成真实刀路
              </el-button>
            </div>
            <JsonResult
              v-if="selected.execution.algorithm"
              :data="selected.execution.algorithm"
              name="algorithm-result"
            />
            <JsonResult
              v-if="selected.execution.toolpath"
              :data="selected.execution.toolpath"
              name="toolpath-result"
            />
            <JsonResult
              v-if="selected.execution.simulation"
              :data="selected.execution.simulation"
              name="cam-engineering-result"
            />
            <el-empty v-else description="尚无工程服务结果" />
          </el-tab-pane>
          <el-tab-pane label="审核与分发" name="dispatch">
            <div class="info-note">
              真实工程仿真通过后才能审核放行。程序接收回执与现场加工反馈分别记录。
            </div>
            <div class="button-group spaced">
              <el-button
                :disabled="!auth.canWrite || selected.status !== 'simulated'"
                @click="approve"
              >
                <FileCheck2 :size="16" />
                审核放行
              </el-button>
              <el-button
                type="primary"
                :disabled="!auth.canWrite || selected.status !== 'approved'"
                @click="dispatch"
              >
                <Send :size="16" />
                分发程序
              </el-button>
              <el-button
                :disabled="!auth.canWrite || selected.status !== 'dispatched'"
                @click="feedbackDialog = true"
              >
                <MessageSquare :size="16" />
                提交反馈
              </el-button>
            </div>
            <JsonResult
              v-if="
                selected.execution.approval ||
                selected.execution.dispatch ||
                selected.execution.feedback
              "
              :data="{
                approval: selected.execution.approval,
                dispatch: selected.execution.dispatch,
                feedback: selected.execution.feedback,
              }"
              name="cam-execution-feedback"
            />
            <el-empty v-else description="暂无审核与执行记录" />
          </el-tab-pane>
          <el-tab-pane label="成果归档" name="artifacts">
            <JsonResult :data="selected" name="cam-project" />
          </el-tab-pane>
        </el-tabs>
      </template>
      <el-empty v-else description="创建加工项目开始工艺规划" />
    </section>
  </div>
  <el-dialog v-model="dialog" title="新建加工项目" width="660px">
    <el-form label-position="top">
      <el-form-item label="项目名称"><el-input v-model="form.name" /></el-form-item>
      <div class="form-grid">
        <el-form-item label="材料"><el-input v-model="form.material" /></el-form-item>
        <el-form-item label="加工资源">
          <el-select v-model="form.resource_id" clearable>
            <el-option
              v-for="resource in resources"
              :key="resource.id"
              :value="resource.id"
              :label="resource.name"
            />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item label="几何文件（可选，真实刀路与仿真必填）">
        <el-select
          v-model="form.geometry_file_id"
          clearable
          placeholder="请先在平台管理上传STEP/STL文件"
        >
          <el-option
            v-for="file in files.filter((f) => /\.(step|stp|stl)$/i.test(f.name))"
            :key="file.id"
            :value="file.id"
            :label="file.name"
          />
        </el-select>
      </el-form-item>
      <template v-if="form.parameters">
        <div class="form-grid">
          <el-form-item
            v-for="(label, key) in names"
            :key="key"
            :label="`${label} (${units[key]})`"
          >
            <el-input-number
              v-model="form.parameters[key]"
              :min="0.01"
              :step="key === 'cut_depth' ? 0.1 : 1"
              controls-position="right"
            />
          </el-form-item>
        </div>
      </template>
      <el-form-item label="项目说明">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" :loading="busy" @click="create">创建项目</el-button>
    </template>
  </el-dialog>
  <el-dialog v-model="feedbackDialog" title="加工执行反馈" width="580px">
    <el-form label-position="top">
      <el-form-item label="现场操作人"><el-input v-model="feedback.operator" /></el-form-item>
      <el-form-item label="质量验收">
        <el-switch v-model="feedback.accepted" active-text="通过" inactive-text="需复核" />
      </el-form-item>
      <el-form-item label="执行结果与质量记录">
        <el-input v-model="feedback.notes" type="textarea" :rows="5" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button type="primary" :loading="busy" @click="submitFeedback">保存反馈</el-button>
    </template>
  </el-dialog>
</template>
