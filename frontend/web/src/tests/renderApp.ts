import { createPinia } from "pinia";
import { flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { createMemoryHistory, type Router } from "vue-router";

import App from "../App.vue";
import { createAppRouter } from "../router";

interface RenderedApp {
  readonly wrapper: VueWrapper;
  readonly router: Router;
}

export const renderAppAt = async (path: string): Promise<RenderedApp> => {
  const router = createAppRouter(createMemoryHistory());
  await router.push(path);

  const wrapper = mount(App, {
    attachTo: document.body,
    global: {
      plugins: [createPinia(), router],
    },
  });

  await router.isReady();
  await flushPromises();

  return { wrapper, router };
};
