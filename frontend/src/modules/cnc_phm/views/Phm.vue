<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { Activity, Plus, Upload, Stethoscope, ClipboardCheck } from '@lucide/vue';
import { ElMessage } from 'element-plus';
import { phmApi } from '../api';
import { api, post, patch, exportJson, type Row } from '../../../services/http';
import { useAuth } from '../../../stores/auth';
import StatusTag from '../../../components/StatusTag.vue';
import JsonResult from '../../../components/JsonResult.vue';
import TrendChart from '../components/TrendChart.vue';
const auth = useAuth(),
  tab = ref('health'),
  busy = ref(false),
  machines = ref<Row[]>([]),
  anomalies = ref<Row[]>([]),
  orders = ref<Row[]>([]),
  machineId = ref(''),
  dialog = ref(''),
  form = ref<Row>({}),
  sampleJson = ref(''),
  diagnosis = ref<Row | null>(null),
  drawer = ref(false),
  rul = ref<Row | null>(null),
  failureThreshold = ref(7.1),
  mode = ref('template'),
  completion = ref('');
const current = computed(() => machines.value.find((m) => m.id === machineId.value)),
  latest = computed(() => current.value?.telemetry.at(-1)),
  filteredEvents = computed(() =>
    anomalies.value.filter((a) => !machineId.value || a.machine_id === machineId.value),
  );
async function load() {
  [machines.value, anomalies.value, orders.value] = await Promise.all([
    phmApi.machines(),
    phmApi.anomalies(),
    phmApi.orders(),
  ]);
  if (!machineId.value) machineId.value = machines.value[0]?.id || '';
}
onMounted(() => load().catch(() => {}));
function open(kind: string, row?: Row) {
  dialog.value = kind;
  form.value =
    kind === 'machine'
      ? {
          name: '',
          code: '',
          component: '主轴',
          thresholds: { vibration_rms: 4.5, temperature: 75 },
        }
      : kind === 'order'
        ? {
            anomaly_id: row!.id,
            title: row!.title + '维护检查',
            assignee: auth.user?.display_name || '',
            actions: ['核查传感器与运行工况', '检查轴承与润滑', '维护后复测振动和温度'],
          }
        : { ...row };
  sampleJson.value = JSON.stringify(
    {
      samples: [{ time: new Date().toISOString(), vibration_rms: 5.5, temperature: 80 }],
    },
    null,
    2,
  );
  completion.value = '';
}
async function save() {
  busy.value = true;
  try {
    if (dialog.value === 'machine') await post('/cnc-phm/machines', form.value);
    else if (dialog.value === 'telemetry')
      await post(`/cnc-phm/machines/${machineId.value}/telemetry`, JSON.parse(sampleJson.value));
    else if (dialog.value === 'order') await post('/cnc-phm/maintenance', form.value);
    else
      await patch('/cnc-phm/maintenance/' + form.value.id, {
        status: 'completed',
        feedback: completion.value,
      });
    dialog.value = '';
    await load();
    ElMessage.success('已保存');
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('采样数据必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
async function diagnose(row: Row) {
  busy.value = true;
  try {
    diagnosis.value = await phmApi.diagnose(row.id, mode.value);
    drawer.value = true;
    await load();
  } catch {
  } finally {
    busy.value = false;
  }
}
async function predict() {
  if (!machineId.value) return;
  busy.value = true;
  try {
    rul.value = await post(`/cnc-phm/machines/${machineId.value}/rul`, {
      failure_threshold: failureThreshold.value,
    });
  } catch {
  } finally {
    busy.value = false;
  }
}
async function startOrder(row: Row) {
  try {
    await patch(`/cnc-phm/maintenance/${row.id}`, { status: 'in_progress' });
    await load();
  } catch {}
}
</script>
<template>
  <div class="toolbar page-toolbar">
    <div class="button-group">
      <el-select
        v-model="machineId"
        placeholder="选择设备"
        style="width: 310px"
        @change="rul = null"
      >
        <el-option
          v-for="machine in machines"
          :key="machine.id"
          :label="machine.name"
          :value="machine.id"
        />
      </el-select>
      <span class="muted">{{ current?.code || '—' }}</span>
    </div>
    <div class="button-group">
      <el-button v-if="auth.canWrite && current" @click="open('telemetry')">
        <Upload :size="15" />
        导入采样
      </el-button>
      <el-button v-if="auth.canWrite" type="primary" @click="open('machine')">
        <Plus :size="16" />
        添加设备
      </el-button>
    </div>
  </div>
  <div class="phm-metrics">
    <div class="metric-panel">
      <small>振动有效值</small>
      <strong>
        {{ latest?.vibration_rms ?? '—' }}
        <em>mm/s</em>
      </strong>
      <span
        :class="latest?.vibration_rms > current?.thresholds.vibration_rms ? 'text-danger' : 'muted'"
      >
        阈值 {{ current?.thresholds.vibration_rms ?? '—' }} mm/s
      </span>
    </div>
    <div class="metric-panel">
      <small>部件温度</small>
      <strong>
        {{ latest?.temperature ?? '—' }}
        <em>°C</em>
      </strong>
      <span
        :class="latest?.temperature > current?.thresholds.temperature ? 'text-danger' : 'muted'"
      >
        阈值 {{ current?.thresholds.temperature ?? '—' }} °C
      </span>
    </div>
    <div class="metric-panel">
      <small>待处理异常</small>
      <strong>
        {{ filteredEvents.filter((e) => e.status !== 'closed').length }}
        <em>项</em>
      </strong>
      <span class="muted">待分析与待维护事件</span>
    </div>
    <div class="metric-panel">
      <small>历史采样</small>
      <strong>
        {{ current?.telemetry.length ?? 0 }}
        <em>点</em>
      </strong>
      <span class="muted">时间对齐后的有效数据</span>
    </div>
  </div>
  <section class="panel" v-loading="busy">
    <el-tabs v-model="tab">
      <el-tab-pane label="设备健康" name="health">
        <div class="panel-header">
          <h3>主轴振动趋势</h3>
          <span class="chart-key">
            <i />
            vibration_rms
          </span>
        </div>
        <TrendChart
          :samples="current?.telemetry || []"
          field="vibration_rms"
          unit="mm/s"
          :threshold="current?.thresholds.vibration_rms"
        />
        <div class="panel-header">
          <h3>部件温度趋势</h3>
          <span class="chart-key">
            <i />
            temperature
          </span>
        </div>
        <TrendChart
          :samples="current?.telemetry || []"
          field="temperature"
          unit="°C"
          :threshold="current?.thresholds.temperature"
        />
      </el-tab-pane>
      <el-tab-pane label="异常与诊断" name="anomalies">
        <div class="toolbar">
          <span class="muted">异常事件 → 证据检索 → 候选原因 → 规则检查</span>
          <el-select v-model="mode" style="width: 220px">
            <el-option value="template" label="规则模板 · 演示" />
            <el-option value="external" label="外部大语言模型" />
          </el-select>
        </div>
        <el-table :data="filteredEvents">
          <el-table-column prop="title" label="异常事件" min-width="290" />
          <el-table-column label="等级" width="90">
            <template #default="{ row }"><StatusTag :value="row.severity" /></template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </el-table-column>
          <el-table-column label="采样值" min-width="170">
            <template #default="{ row }">
              {{ row.measurements.vibration_rms }} mm/s · {{ row.measurements.temperature }} °C
            </template>
          </el-table-column>
          <el-table-column label="操作" width="230">
            <template #default="{ row }">
              <el-button
                v-if="auth.canWrite && row.status !== 'closed'"
                link
                type="primary"
                @click="diagnose(row)"
              >
                候选分析
              </el-button>
              <el-button
                v-if="row.diagnosis.candidates"
                link
                @click="
                  diagnosis = row;
                  drawer = true;
                "
              >
                查看
              </el-button>
              <el-button
                v-if="auth.canWrite && row.status === 'diagnosed'"
                link
                type="primary"
                @click="open('order', row)"
              >
                创建工单
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="RUL趋势估计" name="rul">
        <div class="info-note">
          按实际采样时间拟合振动指标趋势并外推至阈值。本方法为可复现示例，未作为经验证的设备寿命模型；数据不足或趋势不稳定时返回不可预测。
        </div>
        <div class="toolbar">
          <div class="button-group">
            <span>失效阈值</span>
            <el-input-number v-model="failureThreshold" :min="0.1" :step="0.1" />
            <span class="muted">mm/s</span>
          </div>
          <el-button type="primary" :disabled="!current" @click="predict">
            <Activity :size="16" />
            运行趋势估计
          </el-button>
        </div>
        <template v-if="rul">
          <div class="rul-result">
            <div>
              <span class="section-kicker">REMAINING TIME ESTIMATE</span>
              <h2>
                {{ rul.remaining_hours ?? '—' }}
                <small>小时</small>
              </h2>
              <StatusTag :value="rul.status" />
            </div>
            <div>
              <p>{{ rul.reason || '以最后采样时间为基准的线性外推结果' }}</p>
              <p class="muted">采样 {{ rul.sample_count }} 点 · R² {{ rul.r_squared ?? '—' }}</p>
              <p class="muted">
                {{ rul.as_of ? new Date(rul.as_of).toLocaleString('zh-CN') : '' }}
              </p>
            </div>
          </div>
          <JsonResult :data="rul" name="rul-trend-result" />
        </template>
      </el-tab-pane>
      <el-tab-pane label="维护工单" name="orders">
        <el-table :data="orders">
          <el-table-column prop="title" label="工单" min-width="280" />
          <el-table-column prop="assignee" label="负责人" width="130" />
          <el-table-column label="状态" width="130">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </el-table-column>
          <el-table-column prop="feedback" label="执行反馈" min-width="190" show-overflow-tooltip />
          <el-table-column v-if="auth.canWrite" label="操作" width="140">
            <template #default="{ row }">
              <el-button
                v-if="row.status === 'pending'"
                link
                type="primary"
                @click="startOrder(row)"
              >
                开始处理
              </el-button>
              <el-button
                v-if="row.status === 'in_progress'"
                link
                type="primary"
                @click="open('completion', row)"
              >
                完成与反馈
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="数据记录" name="data">
        <div class="toolbar">
          <span class="muted">设备最近采样记录，时间以浏览器时区显示</span>
          <el-button @click="exportJson('machine-telemetry', current)">导出数据</el-button>
        </div>
        <el-table :data="[...(current?.telemetry || [])].reverse().slice(0, 200)">
          <el-table-column label="采样时间" min-width="220">
            <template #default="{ row }">{{ new Date(row.time).toLocaleString('zh-CN') }}</template>
          </el-table-column>
          <el-table-column prop="vibration_rms" label="振动 (mm/s)" />
          <el-table-column prop="temperature" label="温度 (°C)" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>
  <el-drawer v-model="drawer" title="候选故障分析" size="720px">
    <template v-if="diagnosis">
      <h2>{{ diagnosis.title }}</h2>
      <div class="info-note">候选原因需要现场确认；测量有效性检查通过不代表故障已确诊。</div>
      <article
        v-for="candidate in diagnosis.diagnosis.candidates"
        :key="candidate.id"
        class="candidate-card"
      >
        <div class="toolbar">
          <h3>{{ candidate.name }}</h3>
          <StatusTag :value="candidate.validation.status" />
        </div>
        <p>{{ candidate.description }}</p>
        <ul>
          <li v-for="action in candidate.actions" :key="action">
            {{ action }}
          </li>
        </ul>
        <small class="muted">引用证据 {{ candidate.evidence_ids.length }} 项</small>
      </article>
      <h3>检索证据</h3>
      <article
        v-for="item in diagnosis.diagnosis.evidence"
        :key="item.evidence_id"
        class="evidence-card"
      >
        <b>{{ item.title }}</b>
        <p>{{ item.text }}</p>
        <small>来源：{{ item.source }}</small>
      </article>
    </template>
  </el-drawer>
  <el-dialog
    :model-value="!!dialog"
    :title="
      (
        {
          machine: '添加设备',
          telemetry: '导入采样数据',
          order: '创建维护工单',
          completion: '完成维护与反馈',
        } as Record<string, string>
      )[dialog]
    "
    width="620px"
    @close="dialog = ''"
  >
    <el-form label-position="top">
      <template v-if="dialog === 'machine'">
        <el-form-item label="设备名称"><el-input v-model="form.name" /></el-form-item>
        <div class="form-grid">
          <el-form-item label="设备编号"><el-input v-model="form.code" /></el-form-item>
          <el-form-item label="监测部件"><el-input v-model="form.component" /></el-form-item>
          <el-form-item label="振动阈值 (mm/s)">
            <el-input-number v-model="form.thresholds.vibration_rms" :min="0.1" :step="0.1" />
          </el-form-item>
          <el-form-item label="温度阈值 (°C)">
            <el-input-number v-model="form.thresholds.temperature" />
          </el-form-item>
        </div>
      </template>
      <template v-else-if="dialog === 'telemetry'">
        <div class="info-note">
          time需为带时区的ISO时间；重复时间点会合并，超限数据产生异常事件。
        </div>
        <el-input v-model="sampleJson" type="textarea" :rows="13" class="code-input" />
      </template>
      <template v-else-if="dialog === 'order'">
        <el-form-item label="工单名称"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="负责人"><el-input v-model="form.assignee" /></el-form-item>
        <el-form-item label="维护检查项">
          <el-input
            v-for="(_, index) in form.actions"
            :key="index"
            v-model="form.actions[index]"
            style="margin-bottom: 8px"
          />
        </el-form-item>
      </template>
      <template v-else>
        <p>{{ form.title }}</p>
        <el-form-item label="实际故障、维护措施及复测结果">
          <el-input v-model="completion" type="textarea" :rows="6" />
        </el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="dialog = ''">取消</el-button>
      <el-button type="primary" :loading="busy" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
