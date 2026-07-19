let accessToken: string | undefined;

export const getAccessToken = (): string | undefined => accessToken;

export const setAccessToken = (token: string): void => {
  accessToken = token;
};

export const clearAccessToken = (): void => {
  accessToken = undefined;
};
