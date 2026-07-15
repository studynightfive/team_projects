import { AxiosError } from "axios";
import type { AxiosAdapter } from "axios";

export const MOCK_NOT_FOUND = "ERR_MOCK_NOT_FOUND";

/**
 * M01 不虚构业务接口。Mock 模式默认拒绝未注册请求，避免意外访问真实网络。
 */
export const mockAdapter: AxiosAdapter = (config) =>
  Promise.reject(
    new AxiosError("当前 Mock 未注册此请求。", MOCK_NOT_FOUND, config),
  );
