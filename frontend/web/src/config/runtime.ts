const explicitRealApi = import.meta.env.VITE_USE_REAL_API;

export const isRealApiMode =
  explicitRealApi === "true" ||
  (explicitRealApi !== "false" &&
    (import.meta.env.MODE === "api" || import.meta.env.PROD));

export const isMockApiMode = !isRealApiMode;
