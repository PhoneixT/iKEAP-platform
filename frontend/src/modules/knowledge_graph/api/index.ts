import { api, post } from '../../../services/http';
export const knowledgeApi = {
  graph: () => api('/knowledge-graph/graph'),
  entities: () => api('/knowledge-graph/entities'),
  relations: () => api('/knowledge-graph/relations'),
  documents: () => api('/knowledge-graph/documents'),
  search: (query: string, hops = 2) => post('/knowledge-graph/search', { query, hops, limit: 8 }),
};
