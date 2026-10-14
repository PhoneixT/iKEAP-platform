<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { Plus, Search, Upload, Download, ArrowRight } from '@lucide/vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { knowledgeApi } from '../api';
import { api, post, put, exportJson, type Row } from '../../../services/http';
import { useAuth } from '../../../stores/auth';
import GraphCanvas from '../components/GraphCanvas.vue';
import JsonResult from '../../../components/JsonResult.vue';
const auth = useAuth(),
  tab = ref('graph'),
  busy = ref(false);
const graph = ref<{ nodes: Row[]; edges: Row[] }>({ nodes: [], edges: [] }),
  entities = ref<Row[]>([]),
  relations = ref<Row[]>([]),
  documents = ref<Row[]>([]);
const query = ref('TC4叶盘加工工艺与刀具选择'),
  hops = ref(2),
  result = ref<Row | null>(null),
  selected = ref<Row | null>(null),
  drawer = ref(false);
const source = ref(''),
  target = ref(''),
  pathResult = ref<Row | null>(null),
  dialog = ref(''),
  editing = ref(''),
  form = ref<Row>({}),
  fileInput = ref<HTMLInputElement>();
const entityNames = computed(() => Object.fromEntries(entities.value.map((e) => [e.id, e.name])));
async function load() {
  const rows = await Promise.all([
    knowledgeApi.graph(),
    knowledgeApi.entities(),
    knowledgeApi.relations(),
    knowledgeApi.documents(),
  ]);
  [graph.value, entities.value, relations.value, documents.value] = rows;
}
onMounted(() => load().catch(() => {}));
async function search() {
  busy.value = true;
  try {
    result.value = await knowledgeApi.search(query.value, hops.value);
    tab.value = 'search';
  } catch {
  } finally {
    busy.value = false;
  }
}
function open(kind: string, row?: Row) {
  dialog.value = kind;
  editing.value = row?.id || '';
  form.value =
    kind === 'entity'
      ? {
          name: '',
          kind: '工艺',
          source: '',
          description: '',
          aliases: [],
          properties: {},
          ...row,
        }
      : kind === 'relation'
        ? { source_id: '', target_id: '', kind: '', source: '', properties: {} }
        : { title: '', content: '', source: '', entity_ids: [] };
}
async function save() {
  const kind = dialog.value;
  const body = { ...form.value };
  delete body.id;
  delete body.created_at;
  delete body.updated_at;
  busy.value = true;
  try {
    const endpoint =
      '/knowledge-graph/' +
      { entity: 'entities', relation: 'relations', document: 'documents' }[kind];
    editing.value ? await put(endpoint + '/' + editing.value, body) : await post(endpoint, body);
    dialog.value = '';
    ElMessage.success('已保存');
    await load();
  } catch {
  } finally {
    busy.value = false;
  }
}
async function remove(row: Row, kind: string) {
  try {
    await ElMessageBox.confirm('删除后相关关系也会移除，确认删除？', '删除确认', {
      type: 'warning',
    });
    await api(`/knowledge-graph/${kind}/${row.id}`, { method: 'DELETE' });
    await load();
  } catch {}
}
async function exportKnowledge() {
  try {
    exportJson('knowledge-package', await api('/knowledge-graph/export'));
  } catch {}
}
async function findPath() {
  if (!source.value || !target.value) return;
  busy.value = true;
  try {
    pathResult.value = await api(
      `/knowledge-graph/paths?source=${source.value}&target=${target.value}&max_hops=4&directed=false`,
    );
  } catch {
  } finally {
    busy.value = false;
  }
}
async function importFile(event: Event) {
  const input = event.target as HTMLInputElement;
  if (!input.files?.[0]) return;
  try {
    const body = JSON.parse(await input.files[0].text());
    await post('/knowledge-graph/import', body);
    ElMessage.success('导入完成');
    await load();
  } catch (e) {
    if (e instanceof SyntaxError) ElMessage.error('请上传有效的JSON知识包');
  } finally {
    input.value = '';
  }
}
</script>
<template>
  <section class="panel">
    <div class="toolbar">
      <div class="inline-stats">
        <span>
          <b>{{ entities.length }}</b>
          实体
        </span>
        <span>
          <b>{{ relations.length }}</b>
          关系
        </span>
        <span>
          <b>{{ documents.length }}</b>
          知识文档
        </span>
      </div>
      <div class="button-group">
        <input ref="fileInput" type="file" accept=".json" hidden @change="importFile" />
        <el-button v-if="auth.canWrite" @click="fileInput?.click()">
          <Upload :size="15" />
          导入知识包
        </el-button>
        <el-button @click="exportKnowledge">
          <Download :size="15" />
          导出
        </el-button>
        <el-button v-if="auth.canWrite" type="primary" @click="open('entity')">
          <Plus :size="16" />
          新增实体
        </el-button>
      </div>
    </div>
    <el-tabs v-model="tab">
      <el-tab-pane label="图谱浏览" name="graph">
        <div class="graph-toolbar">
          <span class="muted">工业实体及其关联路径</span>
          <div class="graph-legend">
            <span>● 工艺</span>
            <span>● 设备</span>
            <span>● 故障</span>
            <span>● 材料</span>
          </div>
        </div>
        <GraphCanvas
          :graph="graph"
          @select="
            (node) => {
              selected = node;
              drawer = true;
            }
          "
        />
      </el-tab-pane>
      <el-tab-pane label="实体管理" name="entities">
        <el-table :data="entities" stripe>
          <el-table-column prop="name" label="实体名称" min-width="180" />
          <el-table-column prop="kind" label="类型" width="100" />
          <el-table-column prop="description" label="说明" min-width="280" show-overflow-tooltip />
          <el-table-column prop="source" label="来源" min-width="210" />
          <el-table-column v-if="auth.canWrite" label="操作" width="140">
            <template #default="{ row }">
              <el-button link type="primary" @click="open('entity', row)">编辑</el-button>
              <el-button link type="danger" @click="remove(row, 'entities')">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="关系管理" name="relations">
        <div class="toolbar">
          <span class="muted">关系方向、类型及来源记录</span>
          <el-button v-if="auth.canWrite" @click="open('relation')">新增关系</el-button>
        </div>
        <el-table :data="relations">
          <el-table-column label="起点实体" min-width="180">
            <template #default="{ row }">{{ entityNames[row.source_id] }}</template>
          </el-table-column>
          <el-table-column prop="kind" label="关系" width="150" />
          <el-table-column label="终点实体" min-width="180">
            <template #default="{ row }">{{ entityNames[row.target_id] }}</template>
          </el-table-column>
          <el-table-column prop="source" label="来源" min-width="220" />
          <el-table-column v-if="auth.canWrite" label="操作" width="80">
            <template #default="{ row }">
              <el-button link type="danger" @click="remove(row, 'relations')">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      <el-tab-pane label="知识文档" name="documents">
        <div class="toolbar">
          <span class="muted">检索证据来源</span>
          <el-button v-if="auth.canWrite" @click="open('document')">新增文档</el-button>
        </div>
        <div class="evidence-grid">
          <article v-for="document in documents" :key="document.id" class="evidence-card">
            <span class="section-kicker">DOCUMENT · V{{ document.version }}</span>
            <h3>{{ document.title }}</h3>
            <p>{{ document.content }}</p>
            <small>{{ document.source }}</small>
          </article>
        </div>
      </el-tab-pane>
      <el-tab-pane label="GraphRAG检索" name="search">
        <div class="search-bar">
          <el-input
            v-model="query"
            placeholder="描述工艺任务、故障症状或知识查询"
            @keyup.enter="search"
          >
            <template #prefix><Search :size="17" /></template>
          </el-input>
          <el-select v-model="hops" style="width: 130px">
            <el-option v-for="n in [0, 1, 2, 3]" :key="n" :value="n" :label="`${n} 跳扩展`" />
          </el-select>
          <el-button type="primary" :loading="busy" @click="search">检索证据</el-button>
        </div>
        <template v-if="result">
          <div class="result-summary">
            检索到 {{ result.entities.length }} 个相关实体、{{ result.evidence.length }} 项证据
            <el-button link @click="exportJson('retrieval-evidence', result)">导出证据</el-button>
          </div>
          <div class="evidence-grid">
            <article v-for="item in result.evidence" :key="item.evidence_id" class="evidence-card">
              <small class="evidence-id">{{ item.evidence_id }}</small>
              <h3>{{ item.title }}</h3>
              <p>{{ item.text }}</p>
              <small>来源：{{ item.source }}</small>
            </article>
          </div>
          <el-empty
            v-if="!result.evidence.length"
            description="未找到证据，请补充知识文档或修改查询"
          />
        </template>
        <el-empty v-else description="输入任务描述，检索图谱与文档证据" />
      </el-tab-pane>
      <el-tab-pane label="多跳路径" name="paths">
        <div class="search-bar">
          <el-select v-model="source" filterable placeholder="起点实体">
            <el-option
              v-for="entity in entities"
              :key="entity.id"
              :value="entity.id"
              :label="entity.name"
            />
          </el-select>
          <ArrowRight :size="20" />
          <el-select v-model="target" filterable placeholder="终点实体">
            <el-option
              v-for="entity in entities"
              :key="entity.id"
              :value="entity.id"
              :label="entity.name"
            />
          </el-select>
          <el-button type="primary" :loading="busy" @click="findPath">查找路径</el-button>
        </div>
        <template v-if="pathResult">
          <div v-for="(path, index) in pathResult.paths" :key="index" class="path-card">
            <b>路径 {{ Number(index) + 1 }} · {{ path.hops }} 跳</b>
            <p>
              {{ path.nodes.map((id: string) => entityNames[id]).join(' → ') }}
            </p>
            <small v-for="edge in path.edges" :key="edge.id" class="muted">
              {{ edge.kind }} / {{ edge.source }}　
            </small>
          </div>
          <el-empty v-if="!pathResult.paths.length" description="指定跳数内不存在路径" />
        </template>
      </el-tab-pane>
    </el-tabs>
  </section>
  <el-drawer v-model="drawer" title="实体详情" size="480px">
    <template v-if="selected">
      <h2>{{ selected.name }}</h2>
      <p class="muted">{{ selected.kind }}</p>
      <p>{{ selected.description }}</p>
      <div class="info-note">来源：{{ selected.source }}</div>
      <JsonResult :data="selected.properties" />
    </template>
  </el-drawer>
  <el-dialog
    :model-value="!!dialog"
    :title="`${editing ? '编辑' : '新增'}${dialog === 'entity' ? '实体' : dialog === 'relation' ? '关系' : '文档'}`"
    width="620px"
    @close="dialog = ''"
  >
    <el-form label-position="top" @submit.prevent="save">
      <template v-if="dialog === 'entity'">
        <div class="form-grid">
          <el-form-item label="实体名称">
            <el-input v-model="form.name" maxlength="120" />
          </el-form-item>
          <el-form-item label="实体类型">
            <el-select v-model="form.kind" filterable allow-create>
              <el-option
                v-for="kind in [
                  '材料',
                  '零件',
                  '设备',
                  '刀具',
                  '工艺',
                  '验证',
                  '部件',
                  '故障',
                  '症状',
                  '维护',
                ]"
                :key="kind"
                :value="kind"
              />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </template>
      <template v-else-if="dialog === 'relation'">
        <el-form-item label="起点实体">
          <el-select v-model="form.source_id" filterable>
            <el-option
              v-for="entity in entities"
              :key="entity.id"
              :label="entity.name"
              :value="entity.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关系类型"><el-input v-model="form.kind" /></el-form-item>
        <el-form-item label="终点实体">
          <el-select v-model="form.target_id" filterable>
            <el-option
              v-for="entity in entities"
              :key="entity.id"
              :label="entity.name"
              :value="entity.id"
            />
          </el-select>
        </el-form-item>
      </template>
      <template v-else>
        <el-form-item label="文档标题"><el-input v-model="form.title" /></el-form-item>
        <el-form-item label="文档内容">
          <el-input v-model="form.content" type="textarea" :rows="6" />
        </el-form-item>
        <el-form-item label="关联实体">
          <el-select v-model="form.entity_ids" multiple filterable>
            <el-option
              v-for="entity in entities"
              :key="entity.id"
              :label="entity.name"
              :value="entity.id"
            />
          </el-select>
        </el-form-item>
      </template>
      <el-form-item label="来源（必填）">
        <el-input v-model="form.source" placeholder="资料名称、版本和定位信息" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialog = ''">取消</el-button>
      <el-button type="primary" :loading="busy" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>
