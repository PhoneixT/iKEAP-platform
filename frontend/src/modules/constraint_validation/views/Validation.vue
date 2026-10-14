<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { ShieldCheck, Plus } from '@lucide/vue';
import { ElMessage } from 'element-plus';
import { validationApi } from '../api';
import { api, post, put, exportJson, type Row } from '../../../services/http';
import StatusTag from '../../../components/StatusTag.vue';
import { useAuth } from '../../../stores/auth';
const auth = useAuth(),
  rules = ref<Row[]>([]),
  reports = ref<Row[]>([]),
  resources = ref<Row[]>([]),
  busy = ref(false),
  tab = ref('validate'),
  report = ref<Row | null>(null),
  drawer = ref(false),
  dialog = ref(false),
  editing = ref('');
const scope = ref('cam'),
  resource = ref(''),
  parameters = ref('{"spindle_speed":3200,"feed_rate":600,"cut_depth":0.3,"tool_diameter":8}'),
  units = ref('{}'),
  semantic = ref('{"entities":[],"relations":[]}');
const form = ref<Row>({}),
  expected = ref('{}');
async function load() {
  [rules.value, reports.value, resources.value] = await Promise.all([
    validationApi.rules(),
    validationApi.reports(),
    api('/platform/resources'),
  ]);
}
onMounted(() => load().catch(() => {}));
function changeScope() {
  parameters.value =
    scope.value === 'cam'
      ? '{"spindle_speed":3200,"feed_rate":600,"cut_depth":0.3,"tool_diameter":8}'
      : '{"vibration_rms":5.4,"temperature":79}';
}
async function validate() {
  busy.value = true;
  try {
    report.value = await validationApi.evaluate({
      name: scope.value === 'cam' ? '工艺参数检查' : '测量有效性检查',
      scope: scope.value,
      parameters: JSON.parse(parameters.value),
      units: JSON.parse(units.value),
      semantic_constraints: JSON.parse(semantic.value),
      resource_id: resource.value || null,
    });
    await load();
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('输入必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
function openRule(row?: Row) {
  editing.value = row?.id || '';
  form.value = {
    name: '',
    scope: 'cam',
    field: '',
    operator: 'between',
    unit: '',
    severity: 'hard',
    enabled: true,
    ...row,
  };
  expected.value = JSON.stringify(row?.expected || { min: 0, max: 100 });
  dialog.value = true;
}
async function saveRule() {
  busy.value = true;
  try {
    const data: Row = { ...form.value, expected: JSON.parse(expected.value) };
    delete data.id;
    delete data.created_at;
    delete data.updated_at;
    delete data.version;
    editing.value
      ? await put('/constraint-validation/rules/' + editing.value, data)
      : await post('/constraint-validation/rules', data);
    dialog.value = false;
    await load();
    ElMessage.success('规则已保存');
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('规则范围必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="panel">
    <el-tabs v-model="tab">
      <el-tab-pane label="参数验证" name="validate">
        <div class="workbench-grid inner-workbench">
          <div class="input-panel">
            <el-form label-position="top">
              <el-form-item label="验证范围">
                <el-radio-group v-model="scope" @change="changeScope">
                  <el-radio-button value="cam">CAM工艺</el-radio-button>
                  <el-radio-button value="phm">PHM测量</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="关联资源">
                <el-select v-model="resource" clearable placeholder="可选：检查资源能力">
                  <el-option v-for="r in resources" :key="r.id" :value="r.id" :label="r.name" />
                </el-select>
              </el-form-item>
              <el-form-item label="待验证参数（JSON）">
                <el-input v-model="parameters" type="textarea" :rows="6" class="code-input" />
              </el-form-item>
              <el-form-item label="参数单位（JSON，可选）">
                <el-input
                  v-model="units"
                  type="textarea"
                  :rows="2"
                  placeholder='{"spindle_speed":"rpm"}'
                />
              </el-form-item>
              <el-form-item label="语义实体与关系约束（JSON，可选）">
                <el-input v-model="semantic" type="textarea" :rows="3" class="code-input" />
              </el-form-item>
              <el-button
                type="primary"
                :loading="busy"
                :disabled="!auth.canWrite"
                @click="validate"
              >
                <ShieldCheck :size="17" />
                执行约束验证
              </el-button>
            </el-form>
          </div>
          <div class="output-panel" v-loading="busy">
            <template v-if="report">
              <div class="report-heading">
                <div>
                  <small class="section-kicker">VALIDATION REPORT</small>
                  <h2>{{ report.name }}</h2>
                </div>
                <StatusTag :value="report.status" />
              </div>
              <div class="info-note">
                硬约束全部通过才标记为通过；缺少参数或资源能力时标记为待确认。
              </div>
              <el-table :data="report.findings">
                <el-table-column prop="rule_name" label="检查项" min-width="170" />
                <el-table-column label="实际值" width="120">
                  <template #default="{ row }">{{ row.value ?? '缺失' }} {{ row.unit }}</template>
                </el-table-column>
                <el-table-column label="结果" width="110">
                  <template #default="{ row }"><StatusTag :value="row.status" /></template>
                </el-table-column>
                <el-table-column prop="reason" label="说明" min-width="140" />
              </el-table>
              <div class="toolbar">
                <small class="muted">报告编号：{{ report.id }}</small>
                <el-button @click="exportJson('validation-report', report)">导出报告</el-button>
              </div>
            </template>
            <el-empty v-else description="执行验证后查看逐项检查结果" />
          </div>
        </div>
      </el-tab-pane>
      <el-tab-pane label="规则库" name="rules">
        <div class="toolbar">
          <span class="muted">数值范围、语义字段与工程规则</span>
          <el-button v-if="auth.canWrite" type="primary" @click="openRule()">
            <Plus :size="16" />
            新增规则
          </el-button>
        </div>
        <el-table :data="rules">
          <el-table-column prop="name" label="规则名称" min-width="180" />
          <el-table-column prop="scope" label="范围" width="90" />
          <el-table-column prop="field" label="字段" min-width="150" />
          <el-table-column prop="operator" label="运算" width="100" />
          <el-table-column label="约束" min-width="150">
            <template #default="{ row }">
              {{ JSON.stringify(row.expected) }} {{ row.unit }}
            </template>
          </el-table-column>
          <el-table-column label="版本" width="80">
            <template #default="{ row }">v{{ row.version }}</template>
          </el-table-column>
          <el-table-column label="启用" width="80">
            <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
          </el-table-column>
          <el-table-column v-if="auth.canWrite" label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="primary" @click="openRule(row)">编辑</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="验证报告" name="reports">
        <el-table :data="reports">
          <el-table-column prop="name" label="报告名称" min-width="240" />
          <el-table-column prop="scope" label="范围" width="100" />
          <el-table-column label="结果" width="130">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </el-table-column>
          <el-table-column label="检查时间" width="190">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                @click="
                  report = row;
                  drawer = true;
                "
              >
                查看
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>
  <el-drawer v-model="drawer" title="验证报告详情" size="720px">
    <template v-if="report">
      <h2>{{ report.name }}</h2>
      <StatusTag :value="report.status" />
      <el-table :data="report.findings">
        <el-table-column prop="rule_name" label="检查项" min-width="170" />
        <el-table-column prop="value" label="实际值" />
        <el-table-column label="约束">
          <template #default="{ row }">{{ JSON.stringify(row.expected) }}</template>
        </el-table-column>
        <el-table-column label="结果" width="110">
          <template #default="{ row }"><StatusTag :value="row.status" /></template>
        </el-table-column>
      </el-table>
      <el-button @click="exportJson('validation-report', report)">导出报告</el-button>
    </template>
  </el-drawer>
  <el-dialog v-model="dialog" :title="editing ? '编辑规则' : '新增规则'" width="590px">
    <el-form label-position="top">
      <el-form-item label="规则名称"><el-input v-model="form.name" /></el-form-item>
      <div class="form-grid">
        <el-form-item label="范围">
          <el-select v-model="form.scope">
            <el-option v-for="s in ['cam', 'phm', 'global']" :key="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数字段"><el-input v-model="form.field" /></el-form-item>
        <el-form-item label="运算符">
          <el-select v-model="form.operator">
            <el-option
              v-for="op in ['between', 'lte', 'gte', 'eq', 'in', 'required']"
              :key="op"
              :value="op"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="单位"><el-input v-model="form.unit" /></el-form-item>
      </div>
      <el-form-item label="约束JSON（between: min/max；lte/gte/eq: value；in: values数组）">
        <el-input v-model="expected" type="textarea" :rows="3" />
      </el-form-item>
      <div class="form-grid">
        <el-form-item label="约束等级">
          <el-select v-model="form.severity">
            <el-option value="hard" label="硬约束" />
            <el-option value="soft" label="软约束" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
      </div>
    </el-form>
    <template #footer>
      <el-button @click="dialog = false">取消</el-button>
      <el-button type="primary" :loading="busy" @click="saveRule">保存规则</el-button>
    </template>
  </el-dialog>
</template>
