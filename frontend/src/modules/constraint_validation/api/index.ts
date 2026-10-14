import { api, post } from '../../../services/http';
export const validationApi = {
  rules: () => api('/constraint-validation/rules'),
  reports: () => api('/constraint-validation/reports'),
  evaluate: (body: any) => post('/constraint-validation/evaluate', body),
};
