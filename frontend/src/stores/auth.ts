import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api, post, type Row } from '../services/http';

export const useAuth = defineStore('auth', () => {
  const user = ref<Row | null>(null);
  const canWrite = computed(() => user.value?.role === 'admin' || user.value?.role === 'engineer');
  async function login(username: string, password: string) {
    const result = await post('/auth/login', { username, password });
    sessionStorage.setItem('ikeap_token', result.access_token);
    user.value = result.user;
  }
  async function load() {
    user.value = await api('/auth/me');
  }
  function logout() {
    user.value = null;
    sessionStorage.removeItem('ikeap_token');
  }
  return { user, canWrite, login, load, logout };
});
