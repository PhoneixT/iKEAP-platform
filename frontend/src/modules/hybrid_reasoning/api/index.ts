import { api, post } from '../../../services/http';
export const reasoningApi = {
  runs: () => api('/hybrid-reasoning/runs'),
  run: (data: any) => post('/hybrid-reasoning/runs', data),
};
