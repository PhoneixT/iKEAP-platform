import { api } from '../../../services/http';
export const platformApi = {
  resources: () => api('/platform/resources'),
  services: () => api('/platform/services'),
  users: () => api('/platform/users'),
  audit: () => api('/platform/audit'),
};
