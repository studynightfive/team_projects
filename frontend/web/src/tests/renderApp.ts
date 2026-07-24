import { createPinia } from "pinia";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createMemoryHistory, type Router } from "vue-router";

import App from "../App.vue";
import { createAppRouter } from "../router";
import type { AuthenticatedUser } from "../services/auth";
import { useSessionStore } from "../stores/session";

interface RenderedApp {
  readonly wrapper: VueWrapper;
  readonly router: Router;
}

export const renderAppAt = async (
  path: string,
  user?: AuthenticatedUser,
): Promise<RenderedApp> => {
  const router = createAppRouter(createMemoryHistory());
  await router.push(path);
  const pinia = createPinia();
  if (user !== undefined) {
    useSessionStore(pinia).setUser(user);
  }

  const wrapper = mount(App, {
    attachTo: document.body,
    global: {
      plugins: [pinia, router],
    },
  });

  await router.isReady();
  await flushPromises();

  return { wrapper, router };
};
