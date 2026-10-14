import platformRoutes from '../modules/platform/routes';
import knowledge_graphRoutes from '../modules/knowledge_graph/routes';
import hybrid_reasoningRoutes from '../modules/hybrid_reasoning/routes';
import constraint_validationRoutes from '../modules/constraint_validation/routes';
import agent_orchestrationRoutes from '../modules/agent_orchestration/routes';
import blisk_camRoutes from '../modules/blisk_cam/routes';
import cnc_phmRoutes from '../modules/cnc_phm/routes';
import { createRouter, createWebHashHistory } from 'vue-router';
import Shell from '../layouts/Shell.vue';

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      component: () => import('../modules/platform/views/Login.vue'),
    },
    {
      path: '/',
      component: Shell,
      children: [
        ...platformRoutes,
        ...knowledge_graphRoutes,
        ...hybrid_reasoningRoutes,
        ...constraint_validationRoutes,
        ...agent_orchestrationRoutes,
        ...blisk_camRoutes,
        ...cnc_phmRoutes,
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
});
router.beforeEach((to) =>
  !sessionStorage.getItem('ikeap_token') && to.path !== '/login' ? '/login' : true,
);
export default router;
