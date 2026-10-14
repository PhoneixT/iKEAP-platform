import { api, post } from '../../../services/http';
export const phmApi = {
  machines: () => api('/cnc-phm/machines'),
  anomalies: () => api('/cnc-phm/anomalies'),
  orders: () => api('/cnc-phm/maintenance'),
  diagnose: (id: string, mode = 'template') => post(`/cnc-phm/anomalies/${id}/diagnose`, { mode }),
};
