<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Plus, Database, Link2, Server, RefreshCw, ShieldCheck } from '@lucide/vue';
import { ElMessage } from 'element-plus';
import { platformApi } from '../api';
import { post, type Row } from '../../../services/http';
import { useAuth } from '../../../stores/auth';
import StatusTag from '../../../components/StatusTag.vue';
import FileManager from '../components/FileManager.vue';
const roleLabels: Record<string, string> = {
  admin: '管理员',
  engineer: '工程师',
  viewer: '查看者',
};
const auth = useAuth(),
  tab = ref('resources'),
  resources = ref<Row[]>([]),
  services = ref<Row[]>([]),
  users = ref<Row[]>([]),
  audits = ref<Row[]>([]),
  dialog = ref(''),
  busy = ref(false),
  form = ref<Row>({}),
  capabilities = ref('{}');
async function load() {
  [resources.value, services.value] = await Promise.all([
    platformApi.resources(),
    platformApi.services(),
  ]);
  if (auth.user?.role === 'admin')
    [users.value, audits.value] = await Promise.all([platformApi.users(), platformApi.audit()]);
}
onMounted(async () => {
  if (!auth.user) await auth.load();
  await load();
});
function open(kind: string) {
  dialog.value = kind;
  form.value =
    kind === 'resource'
      ? { name: '', kind: 'machine', status: 'available', description: '' }
      : { username: '', display_name: '', password: '', role: 'engineer' };
  capabilities.value = '{"max_rpm":12000,"max_feed":8000,"max_power":30}';
}
async function save() {
  busy.value = true;
  try {
    await post(
      '/platform/' + (dialog.value === 'resource' ? 'resources' : 'users'),
      dialog.value === 'resource'
        ? { ...form.value, capabilities: JSON.parse(capabilities.value) }
        : form.value,
    );
    dialog.value = '';
    await load();
    ElMessage.success('已创建');
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('能力参数必须为有效JSON');
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <section class="panel">
    <el-tabs v-model="tab">
      <el-tab-pane label="资源中心" name="resources">
        <div class="toolbar">
          <span class="muted">设备、软件与计算资源的能力档案</span>
          <el-button v-if="auth.canWrite" type="primary" @click="open('resource')">
            <Plus :size="16" />
            登记资源
          </el-button>
        </div>
        <el-table :data="resources">
          <el-table-column prop="name" label="资源名称" min-width="240" />
          <el-table-column prop="kind" label="类型" width="120" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }"><StatusTag :value="row.status" /></template>
          </el-table-column>
          <el-table-column label="能力参数" min-width="250">
            <template #default="{ row }">
              <code>{{ JSON.stringify(row.capabilities) }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="说明" min-width="250" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="文件管理" name="files"><FileManager /></el-tab-pane>
      <el-tab-pane label="服务与协议" name="services">
        <div class="toolbar">
          <span class="muted">外部服务凭据由后端环境配置管理</span>
          <el-button @click="load">
            <RefreshCw :size="15" />
            刷新状态
          </el-button>
        </div>
        <div class="service-grid">
          <article v-for="service in services" :key="service.name" class="service-card">
            <div class="toolbar">
              <span class="service-icon"><Server :size="20" /></span>
              <StatusTag :value="service.configured ? 'available' : 'offline'" />
            </div>
            <h3>{{ service.name }}</h3>
            <p>{{ service.description }}</p>
            <div>
              <code>{{ service.version }}</code>
              <small>{{ service.kind }}</small>
            </div>
          </article>
        </div>
        <div class="info-note">
          外部服务的“可用”表示连接信息已配置，实际调用结果由业务运行记录确认。当前图谱与检索数据均保存在MySQL。
        </div>
      </el-tab-pane>
      <el-tab-pane v-if="auth.user?.role === 'admin'" label="用户与权限" name="users">
        <div class="toolbar">
          <span class="muted">管理员、工程师与查看者三个角色；当前为共享工作空间</span>
          <el-button type="primary" @click="open('user')">
            <Plus :size="16" />
            创建账户
          </el-button>
        </div>
        <el-table :data="users">
          <el-table-column prop="username" label="用户名" />
          <el-table-column prop="display_name" label="姓名" />
          <el-table-column label="角色">
            <template #default="{ row }">{{ roleLabels[row.role] }}</template>
          </el-table-column>
          <el-table-column label="状态">
            <template #default="{ row }">{{ row.active ? '启用' : '停用' }}</template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="190">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane v-if="auth.user?.role === 'admin'" label="操作审计" name="audit">
        <el-table :data="audits">
          <el-table-column prop="actor" label="操作人" width="140" />
          <el-table-column prop="action" label="操作" min-width="220" />
          <el-table-column prop="target" label="对象编号" min-width="280" />
          <el-table-column label="时间" min-width="200">
            <template #default="{ row }">
              {{ new Date(row.created_at).toLocaleString('zh-CN') }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </section>
  <el-dialog
    :model-value="!!dialog"
    :title="dialog === 'resource' ? '登记资源' : '创建账户'"
    width="600px"
    @close="dialog = ''"
  >
    <el-form label-position="top">
      <template v-if="dialog === 'resource'">
        <el-form-item label="资源名称"><el-input v-model="form.name" /></el-form-item>
        <div class="form-grid">
          <el-form-item label="类型">
            <el-select v-model="form.kind">
              <el-option
                v-for="kind in ['machine', 'software', 'compute', 'data']"
                :key="kind"
                :value="kind"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status">
              <el-option value="available" label="可用" />
              <el-option value="offline" label="离线" />
              <el-option value="maintenance" label="维护中" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="能力参数（JSON）">
          <el-input v-model="capabilities" type="textarea" :rows="4" class="code-input" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </template>
      <template v-else>
        <el-form-item label="用户名">
          <el-input v-model="form.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="姓名"><el-input v-model="form.display_name" /></el-form-item>
        <el-form-item label="初始密码（至少12位）">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role">
            <el-option value="admin" label="管理员" />
            <el-option value="engineer" label="工程师" />
            <el-option value="viewer" label="查看者" />
          </el-select>
        </el-form-item>
      </template>
    </el-form>
    <template #footer>
      <el-button @click="dialog = ''">取消</el-button>
      <el-button type="primary" :loading="busy" @click="save">创建</el-button>
    </template>
  </el-dialog>
</template>
