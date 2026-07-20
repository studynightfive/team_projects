/**
 * 敏感词过滤 API 服务
 *
 * POST /api/v1/sensitive-check
 *
 * 前端在用户点击"发送"时调用此接口进行预检。
 * 如果返回 passed=false，前端弹出警告阻止发送。
 */

import { apiClient } from "../api/client";
import { unwrapApiData, type ApiResponse } from "../api/contracts";

// ============================================================
// 请求/响应类型
// ============================================================
export interface SensitiveCheckRequest {
  readonly question: string;
}

export interface SensitiveCheckResponse {
  readonly passed: boolean;
  readonly verdict: "pass" | "regex" | "bert";
  readonly reason: string;
  readonly regex_matches: readonly string[];
  readonly bert_confidence: number;
  readonly bert_label: string;
}

// ============================================================
// API 调用
// ============================================================
/**
 * 对用户输入问题进行敏感词预检
 *
 * @param question - 用户输入的问题文本
 * @param signal - 可选的 AbortSignal 用于取消请求
 * @returns 检查结果，包含 passed 状态和详细的过滤信息
 */
export const checkSensitiveWords = async (
  question: string,
  signal?: AbortSignal,
): Promise<SensitiveCheckResponse> => {
  const response = await apiClient.post<
    ApiResponse<SensitiveCheckResponse>
  >("/v1/sensitive-check", { question }, { signal });
  return unwrapApiData(response.data);
};
