<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Upload, Download, RefreshCw } from '@lucide/vue';
import { ElMessage } from 'element-plus';
import { api, type Row } from '../../../services/http';
import { useAuth } from '../../../stores/auth';
const auth = useAuth(),
  files = ref<Row[]>([]),
  input = ref<HTMLInputElement>(),
  busy = ref(false);
async function load() {
  files.value = await api('/platform/files');
}
onMounted(() => load().catch(() => {}));
async function upload(event: Event) {
  const target = event.target as HTMLInputElement,
    file = target.files?.[0];
  if (!file) return;
  if (file.size > 20 * 1024 * 1024) {
    ElMessage.error('文件不能超过20MB');
    target.value = '';
    return;
  }
  busy.value = true;
  try {
    const body = new FormData();
    body.append('file', file);
    const response = await fetch((import.meta.env.VITE_API_BASE || '/api/v1') + '/platform/files', {
      method: 'POST',
      headers: {
        Authorization: 'Bearer ' + sessionStorage.getItem('ikeap_token'),
      },
      body,
    });
    if (!response.ok) {
      const result = await response.json();
      throw new Error(String(result.detail));
    }
    await load();
    ElMessage.success('文件已上传');
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '上传失败');
  } finally {
    busy.value = false;
    target.value = '';
  }
}
async function download(file: Row) {
  try {
    const response = await fetch(
      (import.meta.env.VITE_API_BASE || '/api/v1') + `/platform/files/${file.id}/download`,
      {
        headers: {
          Authorization: 'Bearer ' + sessionStorage.getItem('ikeap_token'),
        },
      },
    );
    if (!response.ok) throw new Error('文件下载失败');
    const url = URL.createObjectURL(await response.blob()),
      link = document.createElement('a');
    link.href = url;
    link.download = file.name;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '下载失败');
  }
}
</script>
<template>
  <div v-loading="busy">
    <div class="toolbar">
      <span class="muted">工业资料与几何文件 · 单文件上限20MB · SHA256校验</span>
      <div class="button-group">
        <input
          ref="input"
          type="file"
          hidden
          accept=".json,.csv,.txt,.step,.stp,.stl,.nc,.pdf,.png"
          @change="upload"
        />
        <el-button @click="load">
          <RefreshCw :size="15" />
          刷新
        </el-button>
        <el-button v-if="auth.canWrite" type="primary" @click="input?.click()">
          <Upload :size="15" />
          上传文件
        </el-button>
      </div>
    </div>
    <el-table :data="files">
      <el-table-column prop="name" label="文件名称" min-width="240" />
      <el-table-column label="大小" width="110">
        <template #default="{ row }">{{ (row.size / 1024).toFixed(1) }} KB</template>
      </el-table-column>
      <el-table-column prop="sha256" label="SHA256" min-width="220" show-overflow-tooltip />
      <el-table-column label="上传时间" min-width="190">
        <template #default="{ row }">
          {{ new Date(row.created_at).toLocaleString('zh-CN') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link type="primary" @click="download(row)">
            <Download :size="14" />
            下载
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
