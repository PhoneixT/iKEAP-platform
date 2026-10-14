import { api, post } from '../../../services/http';
export const orchestrationApi = {
  agents: () => api('/agent-orchestration/agents'),
  workflows: () => api('/agent-orchestration/workflows'),
  jobs: () => api('/agent-orchestration/jobs'),
  run: (id: string, context: any) =>
    post(`/agent-orchestration/workflows/${id}/run`, {
      context,
      idempotency_key: crypto.randomUUID(),
    }),
};
