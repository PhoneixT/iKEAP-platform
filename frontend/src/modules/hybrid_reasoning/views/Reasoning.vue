<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Play, FileCheck2, BookOpen, ArrowRight } from '@lucide/vue';
import { ElMessage } from 'element-plus';
import { reasoningApi } from '../api';
import { api, post, exportJson, type Row } from '../../../services/http';
import { useAuth } from '../../../stores/auth';
import StatusTag from '../../../components/StatusTag.vue';
import JsonResult from '../../../components/JsonResult.vue';
const contextPreview = ref<Row | null>(null),
  previewDialog = ref(false);
async function previewContext() {
  busy.value = true;
  try {
    contextPreview.value = await post('/hybrid-reasoning/context', {
      task: task.value,
      domain: domain.value,
      mode: mode.value,
      parameters: JSON.parse(parameters.value),
      resource_id: resource.value || null,
    });
    previewDialog.value = true;
  } catch (error) {
    if (error instanceof SyntaxError) ElMessage.error('参数必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
const auth = useAuth(),
  busy = ref(false),
  runs = ref<Row[]>([]),
  current = ref<Row | null>(null),
  resources = ref<Row[]>([]);
const task = ref('请为TC4整体叶盘规划粗加工、半精加工与精加工工序，并检查刀具与工艺参数。'),
  domain = ref('cam'),
  mode = ref('template'),
  resource = ref(''),
  parameters = ref('{"spindle_speed":3200,"feed_rate":600,"cut_depth":0.3,"tool_diameter":8}'),
  detail = ref(false);
async function load() {
  runs.value = await reasoningApi.runs();
  resources.value = await api('/platform/resources');
}
onMounted(() => load().catch(() => {}));
function changeDomain() {
  parameters.value =
    domain.value === 'cam'
      ? '{"spindle_speed":3200,"feed_rate":600,"cut_depth":0.3,"tool_diameter":8}'
      : '{"vibration_rms":5.4,"temperature":79}';
  task.value =
    domain.value === 'cam'
      ? 'TC4整体叶盘加工工艺规划与刀具选择'
      : '主轴振动超限且温升异常，请检索故障原因和维护检查项';
}
async function run(correct = false) {
  busy.value = true;
  try {
    const data = {
      task: task.value,
      domain: domain.value,
      mode: mode.value,
      parameters: JSON.parse(parameters.value),
      resource_id: resource.value || null,
    };
    current.value =
      correct && current.value
        ? await post(`/hybrid-reasoning/runs/${current.value.id}/correct`, data)
        : await reasoningApi.run(data);
    await load();
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('参数必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="workbench-grid">
    <section class="panel input-panel">
      <div class="panel-header">
        <h3>工业任务</h3>
        <span class="section-kicker">INPUT</span>
      </div>
      <el-form label-position="top">
        <el-form-item label="任务类型">
          <el-radio-group v-model="domain" @change="changeDomain">
            <el-radio-button value="cam">工艺规划</el-radio-button>
            <el-radio-button value="phm">故障分析</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="任务描述">
          <el-input v-model="task" type="textarea" :rows="5" maxlength="5000" show-word-limit />
        </el-form-item>
        <el-form-item label="运行模式">
          <el-select v-model="mode">
            <el-option value="template" label="规则模板 · 演示" />
            <el-option value="external" label="外部大语言模型服务" />
          </el-select>
        </el-form-item>
        <el-form-item label="资源约束（可选）">
          <el-select v-model="resource" clearable placeholder="选择关联资源">
            <el-option
              v-for="item in resources"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="工业参数（JSON）">
          <el-input v-model="parameters" type="textarea" :rows="4" class="code-input" />
        </el-form-item>
        <div class="info-note">
          {{
            mode === 'template'
              ? '模板模式生成示例候选组合，不调用大语言模型。每个候选组合均执行规则验证。'
              : '由后端调用已配置的模型服务，输出需经过结构、证据引用和规则校验。'
          }}
        </div>
        <el-button class="full-width" :loading="busy" @click="previewContext">
          预览任务与上下文
        </el-button>
        <el-button
          type="primary"
          class="full-width"
          :loading="busy"
          :disabled="!auth.canWrite"
          @click="run()"
        >
          <Play :size="16" />
          生成候选方案
        </el-button>
      </el-form>
    </section>
    <section class="panel output-panel" v-loading="busy">
      <div class="panel-header">
        <h3>候选方案</h3>
        <div v-if="current" class="button-group">
          <el-button link @click="detail = true">查看证据</el-button>
          <el-button link @click="exportJson('reasoning-run', current)">导出结果</el-button>
        </div>
      </div>
      <template v-if="current">
        <div class="result-summary">
          <span>
            {{ current.service_metadata.result_source || current.service_metadata.model }} ·
            {{ current.candidates.length }} 个候选
          </span>
          <el-button link type="primary" :disabled="!auth.canWrite" @click="run(true)">
            按当前参数修正
            <ArrowRight :size="14" />
          </el-button>
        </div>
        <article
          v-for="(candidate, index) in current.candidates"
          :key="candidate.id"
          class="candidate-card"
        >
          <div class="candidate-heading">
            <span class="candidate-number">0{{ Number(index) + 1 }}</span>
            <h3>{{ candidate.name }}</h3>
            <StatusTag :value="candidate.validation.status" />
          </div>
          <p>{{ candidate.description }}</p>
          <div class="parameter-grid">
            <div v-for="(value, key) in candidate.parameters" :key="key">
              <small>{{ key }}</small>
              <b>{{ value }}</b>
            </div>
          </div>
          <div class="candidate-actions">
            <span v-for="(action, index) in candidate.actions" :key="index">
              {{ Number(index) + 1 }}. {{ action }}
            </span>
          </div>
          <div class="candidate-footer">
            <span>
              <BookOpen :size="14" />
              {{ candidate.evidence_ids.length }} 项引用证据
            </span>
            <span>
              <FileCheck2 :size="14" />
              {{ candidate.validation.findings.length }} 项约束检查
            </span>
          </div>
          <details>
            <summary>展开验证明细</summary>
            <div
              v-for="(finding, fi) in candidate.validation.findings"
              :key="fi"
              class="finding-row"
            >
              <span>{{ finding.rule_name }}</span>
              <span>{{ finding.value }} {{ finding.unit }}</span>
              <StatusTag :value="finding.status" />
            </div>
          </details>
        </article>
      </template>
      <el-empty v-else description="提交工业任务，生成包含证据与验证结果的候选方案" />
    </section>
  </div>
  <section class="panel">
    <div class="panel-header">
      <h3>运行记录</h3>
      <span class="muted">{{ runs.length }} 条</span>
    </div>
    <el-table :data="runs" @row-click="(row: Row) => (current = row)" class="clickable-table">
      <el-table-column prop="title" label="任务" min-width="320" show-overflow-tooltip />
      <el-table-column label="业务类型" width="130">
        <template #default="{ row }">{{ row.domain === 'cam' ? '工艺规划' : '故障分析' }}</template>
      </el-table-column>
      <el-table-column label="模式" width="160">
        <template #default="{ row }">
          {{ row.mode === 'template' ? '规则模板 · 演示' : '外部模型' }}
        </template>
      </el-table-column>
      <el-table-column label="时间" width="200">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
    </el-table>
  </section>
  <el-drawer v-model="detail" title="检索证据" size="620px">
    <article
      v-for="item in current?.evidence.evidence"
      :key="item.evidence_id"
      class="evidence-card"
    >
      <small class="evidence-id">{{ item.evidence_id }}</small>
      <h3>{{ item.title }}</h3>
      <p>{{ item.text }}</p>
      <small>来源：{{ item.source }}</small>
    </article>
  </el-drawer>
  <el-dialog v-model="previewDialog" title="任务与上下文预览" width="780px">
    <template v-if="contextPreview">
      <h3>任务解析</h3>
      <p class="muted">
        {{ contextPreview.task_specification.intent }} ·
        {{ contextPreview.task_specification.deliverables.join(' / ') }}
      </p>
      <div class="info-note">
        待确认：{{ contextPreview.task_specification.needs_confirmation.join('、') }}
      </div>
      <h3>检索证据</h3>
      <article
        v-for="item in contextPreview.evidence.evidence"
        :key="item.evidence_id"
        class="evidence-card"
      >
        <b>{{ item.title }}</b>
        <p>{{ item.text }}</p>
        <small>{{ item.source }}</small>
      </article>
      <JsonResult :data="contextPreview.task_specification" name="task-specification" />
    </template>
  </el-dialog>
</template>
