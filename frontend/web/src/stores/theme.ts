import { defineStore } from "pinia";
import { computed, ref } from "vue";

export const THEME_STORAGE_KEY = "team-projects-theme-mode";

export type ThemeMode = "system" | "light" | "dark";
export type ResolvedTheme = Exclude<ThemeMode, "system">;

const isThemeMode = (value: string | null): value is ThemeMode =>
  value === "system" || value === "light" || value === "dark";

const readStoredThemeMode = (): ThemeMode => {
  if (typeof window === "undefined") return "system";

  try {
    const storedMode = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemeMode(storedMode) ? storedMode : "system";
  } catch {
    return "system";
  }
};

const systemPrefersDark = (): boolean =>
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-color-scheme: dark)").matches;

export const useThemeStore = defineStore("theme", () => {
  const mode = ref<ThemeMode>(readStoredThemeMode());
  const prefersDark = ref(systemPrefersDark());
  const resolvedTheme = computed<ResolvedTheme>(() =>
    mode.value === "system"
      ? prefersDark.value
        ? "dark"
        : "light"
      : mode.value,
  );

  let colorSchemeQuery: MediaQueryList | undefined;

  const applyTheme = (): void => {
    if (typeof document === "undefined") return;
    document.documentElement.dataset.theme = resolvedTheme.value;
    document.documentElement.style.colorScheme = resolvedTheme.value;
  };

  const handleSystemThemeChange = (event: MediaQueryListEvent): void => {
    prefersDark.value = event.matches;
    applyTheme();
  };

  const startSystemThemeListener = (): void => {
    if (
      colorSchemeQuery !== undefined ||
      typeof window === "undefined" ||
      typeof window.matchMedia !== "function"
    ) {
      applyTheme();
      return;
    }

    colorSchemeQuery = window.matchMedia("(prefers-color-scheme: dark)");
    prefersDark.value = colorSchemeQuery.matches;
    colorSchemeQuery.addEventListener("change", handleSystemThemeChange);
    applyTheme();
  };

  const stopSystemThemeListener = (): void => {
    colorSchemeQuery?.removeEventListener("change", handleSystemThemeChange);
    colorSchemeQuery = undefined;
  };

  const setThemeMode = (nextMode: ThemeMode): void => {
    mode.value = nextMode;

    if (typeof window !== "undefined") {
      try {
        if (nextMode === "system") {
          window.localStorage.removeItem(THEME_STORAGE_KEY);
        } else {
          window.localStorage.setItem(THEME_STORAGE_KEY, nextMode);
        }
      } catch {
        // 浏览器禁用存储时仍保持当前会话内主题可用。
      }
    }

    applyTheme();
  };

  const resetThemeMode = (): void => setThemeMode("system");

  return {
    mode,
    resolvedTheme,
    startSystemThemeListener,
    stopSystemThemeListener,
    setThemeMode,
    resetThemeMode,
  };
});
