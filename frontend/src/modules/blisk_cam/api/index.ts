import { api, post } from '../../../services/http';
export const camApi = {
  projects: () => api('/blisk-cam/projects'),
  action: (id: string, action: string, body: any = {}) =>
    post(`/blisk-cam/projects/${id}/${action}`, body),
};
