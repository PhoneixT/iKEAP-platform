import { ElMessage } from 'element-plus';

export type Row = Record<string, any>;
const base = import.meta.env.VITE_API_BASE || '/api/v1';

export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem('ikeap_token');
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  try {
    const response = await fetch(base + path, {
      ...options,
      headers: { ...headers, ...options.headers },
      signal: options.signal || AbortSignal.timeout(90000),
    });
    if (!response.ok) {
      let detail: any = await response.json().catch(() => ({ detail: '请求失败' }));
      detail = detail.detail || '请求失败';
      if (Array.isArray(detail))
        detail = detail.map((d: Row) => `${d.loc?.slice(1).join('.')}: ${d.msg}`).join('；');
      if (response.status === 401 && path !== '/auth/login') {
        sessionStorage.removeItem('ikeap_token');
        window.location.hash = '#/login';
      }
      throw new Error(String(detail));
    }
    return await response.json();
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : '网络连接失败');
    throw error;
  }
}

export const post = <T = any>(path: string, body: any = {}) =>
  api<T>(path, { method: 'POST', body: JSON.stringify(body) });
export const put = <T = any>(path: string, body: any = {}) =>
  api<T>(path, { method: 'PUT', body: JSON.stringify(body) });
export const patch = <T = any>(path: string, body: any = {}) =>
  api<T>(path, { method: 'PATCH', body: JSON.stringify(body) });

export function exportJson(name: string, data: any) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json;charset=utf-8',
    }),
  );
  const link = document.createElement('a');
  link.href = url;
  link.download = name + '.json';
  link.click();
  URL.revokeObjectURL(url);
}
